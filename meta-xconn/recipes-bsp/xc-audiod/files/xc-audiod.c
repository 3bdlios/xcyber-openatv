/* SPDX-License-Identifier: GPL-2.0-or-later */
/* XC native DVB audio backend: application control stays on audio0. */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>
#include <time.h>
#include <signal.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <math.h>
#include <sys/ioctl.h>
#include <linux/dvb/dmx.h>
#include <alsa/asoundlib.h>
#include <libavcodec/avcodec.h>
#include <libavutil/channel_layout.h>
#include <libswresample/swresample.h>
#include "sync_control.h"
struct state {unsigned gen;int demux,pid,codec,play,source,mute;unsigned left,right;int channel;};
static volatile sig_atomic_t quit;
static void stop(int n){(void)n;quit=1;}
static int state_read(struct state *s){FILE *f=fopen("/proc/xc_audio","r");int n;if(!f)return -1;n=fscanf(f,"%u %d %d %d %d %d %d %u %u %d",&s->gen,&s->demux,&s->pid,&s->codec,&s->play,&s->source,&s->mute,&s->left,&s->right,&s->channel);fclose(f);return n==10?0:-1;}
static int syswrite(const char *path,const char *v){int fd=open(path,O_WRONLY|O_CLOEXEC);if(fd<0)return -1;int n=write(fd,v,strlen(v));close(fd);return n<0?-1:0;}
static enum AVCodecID codec_id(int bypass){switch(bypass){case 1:return AV_CODEC_ID_MP2;case 0:return AV_CODEC_ID_AC3;case 8:return AV_CODEC_ID_AAC;/* Enigma2 AAC-HE (9) is DVB stream type 0x11: LATM/LOAS, not ADTS */case 9:return AV_CODEC_ID_AAC_LATM;case 2:case 16:return AV_CODEC_ID_DTS;case 34:return AV_CODEC_ID_EAC3;default:return AV_CODEC_ID_NONE;}}
struct engine {struct state initial;int fd;AVCodecContext *dec;AVCodecParserContext *parser;AVFrame *frame;AVPacket *packet;SwrContext *swr;snd_pcm_t *pcm;int rate,format,channels,started,paused,cc,cc_valid,fileclock,audiomaster;uint8_t header[272];int hn,need;int64_t pts,nextpts;
 int64_t t_next,startup_begin;struct xc_sync sync;int startup_dropped,xruns; struct xc_start_clock start_clock;};
static void engine_close(struct engine *e){if(e->fd>=0){ioctl(e->fd,DMX_STOP);close(e->fd);}if(e->pcm){snd_pcm_drop(e->pcm);snd_pcm_close(e->pcm);}swr_free(&e->swr);avcodec_free_context(&e->dec);if(e->parser)av_parser_close(e->parser);av_frame_free(&e->frame);av_packet_free(&e->packet);memset(e,0,sizeof(*e));e->fd=-1;}
/* How far the stream relay / file input may run ahead of the picture clock (aml_hardware_dmx, ms):
 * the default 1 s is about the sound's own lag in relay streams, so the sound came late. 2 s costs
 * one more second before a relay channel shows. */
static void hiu_lead(void){syswrite("/sys/module/aml_hardware_dmx/parameters/xc_es_start_ms","2000");syswrite("/sys/module/aml_hardware_dmx/parameters/xc_es_lead_ms","2000");}
static int engine_open(struct engine *e,struct state *s){char path[128];enum AVCodecID id=codec_id(s->codec);const AVCodec *c=avcodec_find_decoder(id);if(!c)return -1;e->initial=*s;e->pts=e->nextpts=AV_NOPTS_VALUE;
 /* The HIU demux is fed by relay/file playback. Its XC video clock is
  * authoritative; audio must not repeatedly realign that same clock. */
 snprintf(path,sizeof(path),"/sys/class/stb/demux%d_source",s->demux);
 FILE *source=fopen(path,"r");if(source){char name[32]={0};if(fgets(name,sizeof(name),source))e->fileclock=!strncmp(name,"hiu",3);fclose(source);}
 e->dec=avcodec_alloc_context3(c);e->parser=av_parser_init(id);e->frame=av_frame_alloc();e->packet=av_packet_alloc();if(!e->dec||!e->parser||!e->frame||!e->packet)return -1;e->dec->pkt_timebase=(AVRational){1,90000};e->dec->thread_count=1;if(avcodec_open2(e->dec,c,NULL)<0)return -1;
 snprintf(path,sizeof(path),"/dev/dvb/adapter0/demux%d",s->demux);e->fd=open(path,O_RDONLY|O_NONBLOCK|O_CLOEXEC);if(e->fd<0)return -1;ioctl(e->fd,DMX_SET_BUFFER_SIZE,2*1024*1024);struct dmx_pes_filter_params p={.pid=s->pid,.input=DMX_IN_FRONTEND,.output=DMX_OUT_TSDEMUX_TAP,.pes_type=DMX_PES_OTHER,.flags=DMX_IMMEDIATE_START};if(ioctl(e->fd,DMX_SET_PES_FILTER,&p)<0)return -1;
 fprintf(stderr,"XC audio generation=%u demux=%d pid=%d bypass=%d decoder=%s\n",s->gen,s->demux,s->pid,s->codec,c->name);return 0;}
static int current(struct engine *e,struct state *s){return !state_read(s)&&s->gen==e->initial.gen&&s->pid==e->initial.pid&&s->play!=0;}
/* Amlogic's discontinuity timer may restore AMASTER after AUDIO_START.
 * Restrict correction to an active HIU engine; tuner playback keeps its policy. */
static void file_clock_guard(struct engine *e){
 if(!e->fileclock||!e->started||e->audiomaster)return;
 FILE *f=fopen("/sys/class/tsync/mode","r");int mode=-1;
 if(f){if(fscanf(f,"%d",&mode)!=1)mode=-1;fclose(f);}
 if(mode>0)syswrite("/sys/class/tsync/mode","0");
}
static int64_t now_ms(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return (int64_t)t.tv_sec*1000+t.tv_nsec/1000000;}
static int clock_read(const char *name,uint32_t *value){
 char path[128];snprintf(path,sizeof(path),"/sys/class/tsync/%s",name);
 FILE *f=fopen(path,"r");if(!f)return -1;unsigned x;int ok=fscanf(f,"%x",&x)==1;fclose(f);if(!ok||!x)return -1;*value=x;return 0;
}
/* Validate the picture clock across decoded frames, not once per frame.
 * Discard stale decoded audio BEFORE playback without sleeping per frame.
 * Never fail open with seconds of known bad timing. */
static int startup_align(struct engine *e,int64_t pts,int count){
 if(!e->fileclock||e->started)return 0;
 if(!e->startup_begin)e->startup_begin=now_ms();
 while(!quit){
  struct state s;if(!current(e,&s))return -1;
  if(s.play==2){usleep(10000);continue;}
  int64_t now=now_ms();uint32_t p=0,v=0;
  if(now-e->startup_begin>6000){
   fprintf(stderr,"XC r13 startup failed: no aligned audio within 6s; retrying cleanly, skipped=%d samples\n",e->startup_dropped);return -1;
  }
  if(clock_read("pts_pcrscr",&p)||clock_read("pts_video",&v)){usleep(5000);continue;}
  if(!xc_start_ready(&e->start_clock,now,p,v)){usleep(5000);continue;}
  int32_t error=xc_delta(p,(uint32_t)pts);
  if(error>2700){
   int64_t skip=((int64_t)error-900)*48000/90000;
   if(skip>count)skip=count;
   e->startup_dropped+=(int)skip;
   return (int)skip;
  }
  if(error<-900){usleep(5000);continue;}
  fprintf(stderr,"XC r13 startup aligned: %+d ms, pre-start skipped=%d samples\n",error/90,e->startup_dropped);
  return 0;
 }
 return -1;
}
static void align_check(struct engine *e,int64_t heard){
 if(!e->fileclock||!e->swr)return;
 int64_t t=now_ms();if(t<e->t_next)return;e->t_next=t+100;
 uint32_t p,v;
 if(clock_read("pts_pcrscr",&p)||clock_read("pts_video",&v)){
  memset(&e->sync,0,sizeof(e->sync));swr_set_compensation(e->swr,0,0);return;
 }
 int result=xc_observe(&e->sync,t,p,v,(uint32_t)heard);
 if(result<0){swr_set_compensation(e->swr,0,0);return;}
 if(result>0){
  int delta=(int)((int64_t)e->sync.ppm*48000*5/1000000);
  int r=swr_set_compensation(e->swr,delta,48000*5);
  fprintf(stderr,"XC r13 soft sync: error=%+d ms rate=%+d ppm rc=%d\n",xc_delta(p,(uint32_t)heard)/90,e->sync.ppm,r);
 }
}
static int emit_frame(struct engine *e,AVFrame *f){struct state s;if(!current(e,&s))return -1;if(!e->pcm){int r=snd_pcm_open(&e->pcm,"xc_native",SND_PCM_STREAM_PLAYBACK,SND_PCM_NONBLOCK);/* xc_native lives in /etc/asound.conf, which other plugins sometimes overwrite: then go to the HDMI device directly */if(r<0){fprintf(stderr,"ALSA open xc_native: %s, using plughw:0,2\n",snd_strerror(r));r=snd_pcm_open(&e->pcm,"plughw:0,2",SND_PCM_STREAM_PLAYBACK,SND_PCM_NONBLOCK);}if(r<0){fprintf(stderr,"ALSA open: %s\n",snd_strerror(r));e->pcm=NULL;return -1;}r=snd_pcm_set_params(e->pcm,SND_PCM_FORMAT_S16_LE,SND_PCM_ACCESS_RW_INTERLEAVED,2,48000,1,80000);if(r<0){fprintf(stderr,"ALSA params: %s\n",snd_strerror(r));return -1;}}
 if(!e->swr||e->rate!=f->sample_rate||e->format!=f->format||e->channels!=f->ch_layout.nb_channels){swr_free(&e->swr);AVChannelLayout stereo=AV_CHANNEL_LAYOUT_STEREO;if(swr_alloc_set_opts2(&e->swr,&stereo,AV_SAMPLE_FMT_S16,48000,&f->ch_layout,f->format,f->sample_rate,0,NULL)<0||swr_init(e->swr)<0)return -1;e->rate=f->sample_rate;e->format=f->format;e->channels=f->ch_layout.nb_channels;}
 int capacity=swr_get_out_samples(e->swr,f->nb_samples);if(capacity<1||capacity>262144)return -1;int16_t *buf=av_malloc_array(capacity*2,sizeof(int16_t));if(!buf)return -1;uint8_t *out=(uint8_t*)buf;int count=swr_convert(e->swr,&out,capacity,(const uint8_t**)f->extended_data,f->nb_samples);if(count<0){av_free(buf);return -1;}
 int64_t pts=f->best_effort_timestamp;if(pts==AV_NOPTS_VALUE)pts=f->pts;if(pts==AV_NOPTS_VALUE)pts=e->nextpts;if(pts==AV_NOPTS_VALUE){av_free(buf);return 0;}/* Source media time must not advance by the compensated output length. */
 int64_t content_ticks=(int64_t)f->nb_samples*90000/f->sample_rate;
 e->nextpts=pts+content_ticks;
 int first=startup_align(e,pts,count);
 if(first<0){av_free(buf);return -1;}
 if(first>=count){av_free(buf);return 0;}
 /* Enigma2 sends its 0..100 volume as 63..0 "dB" (63 - vol*63/100). Taken literally that is
    -31.5 dB at 50%, far too quiet; use linear amplitude instead: gain = level
    (20*log10: 50% -6 dB, 25% -12 dB, 10% -20 dB), same as xc-volume-bridge. */
 double gl=s.mute||s.left>=63?0:(63.0-s.left)/63.0,gr=s.mute||s.right>=63?0:(63.0-s.right)/63.0;for(int i=0;i<count;i++){int16_t a=buf[2*i],b=buf[2*i+1];if(s.channel==1)b=a;else if(s.channel==2)a=b;else if(s.channel==3)a=b=(int16_t)(((int)a+b)/2);else if(s.channel==4){int16_t t=a;a=b;b=t;}buf[2*i]=(int16_t)(a*gl);buf[2*i+1]=(int16_t)(b*gr);}
 int64_t blocked_since=0;uint32_t blocked_video=0;
 int offset=first;while(offset<count&&!quit){if(!current(e,&s)){av_free(buf);return -1;}if(s.play==2){blocked_since=0;if(!e->paused){snd_pcm_pause(e->pcm,1);e->paused=1;}usleep(10000);continue;}if(e->paused){snd_pcm_pause(e->pcm,0);e->paused=0;}snd_pcm_sframes_t n=snd_pcm_writei(e->pcm,buf+offset*2,count-offset);if(n==-EAGAIN||n==0){
  /* A HIU pause/seek can leave ALSA RUNNING with a full, frozen ring.
     Only recover after the picture advances: a real pause must stay paused. */
  if(e->fileclock){
   uint32_t video=0;
   if(!clock_read("pts_video",&video)){
    if(!blocked_since){blocked_since=now_ms();blocked_video=video;}
    else if(now_ms()-blocked_since>750&&xc_delta(video,blocked_video)>9000){
     fprintf(stderr,"XC PCM stalled after HIU resume; reopening gen=%u\n",s.gen);
     av_free(buf);return -1;
    }
   }
  }
  usleep(5000);continue;
 }
 blocked_since=0;if(n<0){
  if(n==-EPIPE){e->xruns++;fprintf(stderr,"XC r13 ALSA underrun #%d gen=%u\n",e->xruns,s.gen);}
  if(snd_pcm_recover(e->pcm,n,1)<0){av_free(buf);return -1;}
  memset(&e->sync,0,sizeof(e->sync));swr_set_compensation(e->swr,0,0);continue;
 }offset+=n;snd_pcm_sframes_t delay=0;snd_pcm_delay(e->pcm,&delay);if(delay<0||delay>48000){memset(&e->sync,0,sizeof(e->sync));delay=0;}
 int64_t heard=pts+((int64_t)offset-delay)*content_ticks/(count?count:1);char value[96];snprintf(value,sizeof(value),"0x%08x",(uint32_t)heard);if(!e->started){char event[128];snprintf(event,sizeof(event),"AUDIO_START:%s",value);if(syswrite("/sys/class/tsync/event",event)<0){av_free(buf);return -1;}if(syswrite("/sys/class/tsync/mode",e->fileclock&&!e->audiomaster?"0":"1")<0){av_free(buf);return -1;}
 e->started=1;e->t_next=now_ms()+1000;fprintf(stderr,"XC audio PCM running pts=%s clock=%s\n",value,e->fileclock&&!e->audiomaster?"XC-video":"audio");}syswrite("/sys/class/tsync/pts_audio",value);file_clock_guard(e);align_check(e,heard);}
 av_free(buf);return quit?-1:0;}
static int decode(struct engine *e,const uint8_t *data,int size){while(size>0){uint8_t *packet=NULL;int length=0;int used=av_parser_parse2(e->parser,e->dec,&packet,&length,data,size,e->pts,e->pts,AV_NOPTS_VALUE);e->pts=AV_NOPTS_VALUE;if(used<0)return -1;if(!used&&!length)break;data+=used;size-=used;if(!length)continue;av_packet_unref(e->packet);if(av_new_packet(e->packet,length)<0)return -1;memcpy(e->packet->data,packet,length);e->packet->pts=e->parser->pts;e->packet->dts=e->parser->dts;int ret=avcodec_send_packet(e->dec,e->packet);if(ret<0&&ret!=AVERROR(EAGAIN))continue;while(avcodec_receive_frame(e->dec,e->frame)>=0){if(emit_frame(e,e->frame)<0)return -1;av_frame_unref(e->frame);}}return 0;}
static int ts(struct engine *e,uint8_t *p){if(p[0]!=0x47||(p[1]&0x80))return 0;int pid=((p[1]&31)<<8)|p[2];if(pid!=e->initial.pid||!(p[3]&0x10)||(p[3]&0xc0))return 0;int cc=p[3]&15;if(e->cc_valid&&cc==e->cc)return 0;if(e->cc_valid&&cc!=((e->cc+1)&15)){avcodec_flush_buffers(e->dec);e->pts=e->nextpts=AV_NOPTS_VALUE;e->need=0;}e->cc=cc;e->cc_valid=1;int at=4;if(p[3]&0x20)at+=1+p[4];if(at>=188)return 0;if(p[1]&0x40){e->hn=0;e->need=9;}while(e->need&&at<188){int n=e->need-e->hn;if(n>188-at)n=188-at;if(n<1||e->hn+n>(int)sizeof(e->header))return -1;memcpy(e->header+e->hn,p+at,n);e->hn+=n;at+=n;if(e->hn==9){if(e->header[0]||e->header[1]||e->header[2]!=1)return -1;e->need=9+e->header[8];}if(e->hn==e->need){if((e->header[7]&0x80)&&e->hn>=14){uint8_t *b=e->header+9;e->pts=((int64_t)(b[0]&14)<<29)|((int64_t)b[1]<<22)|((b[2]&254)<<14)|(b[3]<<7)|(b[4]>>1);}e->need=0;}}
 return at<188&&!e->need?decode(e,p+at,188-at):0;}
int main(void){signal(SIGTERM,stop);signal(SIGINT,stop);hiu_lead();setvbuf(stderr,NULL,_IOLBF,0);av_log_set_level(AV_LOG_WARNING);struct engine e={.fd=-1};struct state s;uint8_t buffer[188*128+AV_INPUT_BUFFER_PADDING_SIZE];int fill=0;
 while(!quit){if(state_read(&s)||s.pid<0||s.play==0||s.source!=0){if(e.dec)engine_close(&e);fill=0;usleep(20000);continue;}if(e.dec&&s.gen!=e.initial.gen){engine_close(&e);fill=0;}if(!e.dec){if(engine_open(&e,&s)<0){perror("XC audio open");engine_close(&e);usleep(200000);continue;}}
 file_clock_guard(&e);if(s.play==2){usleep(10000);continue;}struct pollfd fd={e.fd,POLLIN,0};if(poll(&fd,1,20)<=0)continue;int n=read(e.fd,buffer+fill,sizeof(buffer)-AV_INPUT_BUFFER_PADDING_SIZE-fill);if(n<=0){if(n==0||errno!=EAGAIN){engine_close(&e);fill=0;}continue;}fill+=n;memset(buffer+fill,0,AV_INPUT_BUFFER_PADDING_SIZE);int off=0,failed=0;while(fill-off>=188){if(buffer[off]!=0x47){off++;continue;}if(ts(&e,buffer+off)<0){failed=1;break;}off+=188;}if(failed){engine_close(&e);fill=0;}else{memmove(buffer,buffer+off,fill-off);fill-=off;}}
 engine_close(&e);return 0;}
