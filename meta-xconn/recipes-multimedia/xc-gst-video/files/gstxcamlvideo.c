/* Encoded GStreamer video sink for the XCEnigma Amlogic decoder ABI. */
#include <gst/gst.h>
#include <gst/base/gstbasesink.h>
#include <gst/video/videooverlay.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <sys/file.h>
#include <poll.h>
#include <errno.h>
#include <string.h>
#include <stdint.h>
#include <stdio.h>
#define PACKAGE "xcenigma-amlvideo"
typedef struct { GstBaseSink parent; int fd,av,lockfd,codec,width,height,fps_n,fps_d; gint flushing; guint64 frames; gchar oldroute[256]; } XcSink;
typedef struct { GstBaseSinkClass parent; } XcSinkClass;
static void overlay_init(GstVideoOverlayInterface *iface);
G_DEFINE_TYPE_WITH_CODE(XcSink,xc_sink,GST_TYPE_BASE_SINK,G_IMPLEMENT_INTERFACE(GST_TYPE_VIDEO_OVERLAY,overlay_init))
static GstStaticPadTemplate pad=GST_STATIC_PAD_TEMPLATE("sink",GST_PAD_SINK,GST_PAD_ALWAYS,GST_STATIC_CAPS(
 "video/x-h264, stream-format=(string)byte-stream, alignment=(string)au; "
 "video/x-h265, stream-format=(string)byte-stream, alignment=(string)au; "
 "video/mpeg, mpegversion=(int){1,2}, systemstream=(boolean)false"));
static gboolean put(const char *path,const char *value){int f=open(path,O_WRONLY|O_CLOEXEC);if(f<0)return FALSE;size_t n=strlen(value);ssize_t r=write(f,value,n);close(f);return r==(ssize_t)n;}
static void remember_route(XcSink *s){
 char buf[2048];int f=open("/sys/class/vfm/map",O_RDONLY|O_CLOEXEC);if(f<0)return;
 ssize_t n=read(f,buf,sizeof(buf)-1);close(f);if(n<0)return;buf[n]=0;
 char *a=strstr(buf," default {");if(!a)return;a=strchr(a,'{')+1;char *b=strchr(a,'}');if(!b)return;
 size_t out=0;while(a<b && out<sizeof(s->oldroute)-1){if(*a=='('){while(a<b&&*a!=')')a++;if(a<b)a++;}else s->oldroute[out++]=*a++;}s->oldroute[out]=0;
}
static void release_decoder(XcSink *s){if(s->fd>=0){close(s->fd);s->fd=-1;}if(s->av>=0){close(s->av);s->av=-1;}}
static gboolean configure_decoder(XcSink *s){
 release_decoder(s);
 if(s->lockfd<0){s->lockfd=open("/run/gt-native-hardware.lock",O_RDWR|O_CREAT|O_CLOEXEC,0600);if(s->lockfd<0||flock(s->lockfd,LOCK_EX|LOCK_NB)<0){GST_ELEMENT_ERROR(s,RESOURCE,BUSY,("Another native player owns the video decoder"),("No decoder routing was changed"));return FALSE;}}
 if(!s->oldroute[0])remember_route(s);
 if(!put("/sys/class/vfm/map","rm default"))return FALSE;
 if(!put("/sys/class/vfm/map",s->codec==11?"add default decoder amvideo":"add default decoder deinterlace amvideo"))return FALSE;
 s->av=open("/dev/amvideo",O_RDWR|O_CLOEXEC);
 gint64 open_deadline=g_get_monotonic_time()+1500000;
 do {
  s->fd=open(s->codec==11?"/dev/amstream_hevc_sched":"/dev/amstream_vbuf",O_WRONLY|O_NONBLOCK|O_CLOEXEC);
  if(s->fd>=0 || errno!=EBUSY || g_atomic_int_get(&s->flushing))break;
  g_usleep(50000);
 } while(g_get_monotonic_time()<open_deadline);
 if(s->fd<0||s->av<0)goto fail;
 if(ioctl(s->fd,0x40045304,(unsigned long)s->codec)<0)goto fail;
 struct {uint32_t format,width,height,rate,extra,status,ratio,padding;uint64_t param,ratio64;} info={0};
 info.format=s->codec==2?4:0;info.width=s->width;info.height=s->height;info.rate=s->fps_n?96000U*s->fps_d/s->fps_n:3840;info.param=0;
 if(ioctl(s->fd,0x4004530a,&info)<0||ioctl(s->fd,0x5311,0UL)<0)goto fail;
 uint32_t zero=0;
 if(ioctl(s->av,0x40045327,&zero)<0||ioctl(s->av,0x40045388,0UL)<0||ioctl(s->av,0x40045317,0UL)<0||ioctl(s->av,0x40045322,1UL)<0)goto fail;
 /* GStreamer schedules video against its selected audio clock. */
 put("/sys/class/tsync/enable","0");
 GST_INFO_OBJECT(s,"Amlogic decoder ready: codec=%d %dx%d %d/%d",s->codec,s->width,s->height,s->fps_n,s->fps_d);return TRUE;
 fail:GST_ELEMENT_ERROR(s,RESOURCE,OPEN_WRITE,("Cannot initialize Amlogic video decoder"),("errno=%d",errno));release_decoder(s);return FALSE;
}
static gboolean start(GstBaseSink *b){XcSink*s=(XcSink*)b;s->frames=0;s->oldroute[0]=0;g_atomic_int_set(&s->flushing,0);return TRUE;}
static gboolean stop(GstBaseSink *b){XcSink*s=(XcSink*)b;release_decoder(s);if(s->lockfd>=0){close(s->lockfd);s->lockfd=-1;}if(s->oldroute[0]){gchar route[320];g_snprintf(route,sizeof(route),"add default %s",s->oldroute);put("/sys/class/vfm/map","rm default");put("/sys/class/vfm/map",route);s->oldroute[0]=0;}return TRUE;}
static gboolean caps(GstBaseSink*b,GstCaps*c){
 XcSink*s=(XcSink*)b;const GstStructure*t=gst_caps_get_structure(c,0);const char*name=gst_structure_get_name(t);int previous_codec=s->codec;
 if(!strcmp(name,"video/x-h264"))s->codec=2;else if(!strcmp(name,"video/x-h265"))s->codec=11;else if(!strcmp(name,"video/mpeg"))s->codec=0;else return FALSE;
 s->width=1920;s->height=1080;s->fps_n=25;s->fps_d=1;
 gst_structure_get_int(t,"width",&s->width);gst_structure_get_int(t,"height",&s->height);gst_structure_get_fraction(t,"framerate",&s->fps_n,&s->fps_d);
 if(s->width<16||s->width>4096||s->height<16||s->height>2160)return FALSE;
 /* Parsers can announce provisional caps before they read the sequence header.
  * Open the decoder with the final caps immediately before its first buffer. */
 if(s->fd>=0 && previous_codec!=s->codec)release_decoder(s);
 return TRUE;
}
static GstFlowReturn render(GstBaseSink*b,GstBuffer*buffer){
 XcSink*s=(XcSink*)b;if(g_atomic_int_get(&s->flushing))return GST_FLOW_FLUSHING;
 if(s->fd<0&&!configure_decoder(s))return GST_FLOW_ERROR;
 GstMapInfo map;if(!gst_buffer_map(buffer,&map,GST_MAP_READ))return GST_FLOW_ERROR;
 if(GST_BUFFER_PTS_IS_VALID(buffer)){guint64 pts=gst_util_uint64_scale(GST_BUFFER_PTS(buffer),90000,GST_SECOND);int32_t low=(int32_t)(uint32_t)pts;if(ioctl(s->fd,0x4004530e,(unsigned long)(long)low)<0){gst_buffer_unmap(buffer,&map);return GST_FLOW_ERROR;}}
 size_t offset=0;gint64 deadline=g_get_monotonic_time()+3000000;
 while(offset<map.size){
  if(g_atomic_int_get(&s->flushing)){gst_buffer_unmap(buffer,&map);return GST_FLOW_FLUSHING;}
  ssize_t n=write(s->fd,map.data+offset,map.size-offset);
  if(n>0){offset+=(size_t)n;deadline=g_get_monotonic_time()+3000000;continue;}
  if(n<0&&(errno==EAGAIN||errno==EINTR)){if(g_get_monotonic_time()>deadline)break;struct pollfd p={s->fd,POLLOUT,0};poll(&p,1,40);continue;}break;
 }
 gboolean ok=offset==map.size;gst_buffer_unmap(buffer,&map);if(!ok){GST_ELEMENT_ERROR(s,RESOURCE,WRITE,("Amlogic video input stalled"),("errno=%d",errno));return GST_FLOW_ERROR;}
 if(++s->frames==1)GST_INFO_OBJECT(s,"First encoded video buffer delivered");return GST_FLOW_OK;
}
static gboolean unlock(GstBaseSink*b){g_atomic_int_set(&((XcSink*)b)->flushing,1);return TRUE;}
static gboolean unlock_stop(GstBaseSink*b){g_atomic_int_set(&((XcSink*)b)->flushing,0);return TRUE;}
static void window(GstVideoOverlay*o,guintptr h){(void)o;(void)h;}
static void rectangle(GstVideoOverlay*o,gint x,gint y,gint w,gint h){(void)o;if(w>0&&h>0){gchar v[96];g_snprintf(v,sizeof(v),"%d %d %d %d",x,y,x+w-1,y+h-1);put("/sys/class/video/axis",v);}}
static void overlay_init(GstVideoOverlayInterface*i){i->set_window_handle=window;i->set_render_rectangle=rectangle;}
static gint64 decoder_time(XcSink*s){(void)s;return GST_CLOCK_TIME_NONE;}
static gint video_width(XcSink*s){return s->width;}
static gint video_height(XcSink*s){return s->height;}
static gint video_rate(XcSink*s){return s->fps_n?1000*s->fps_n/s->fps_d:0;}
static gint video_codec(XcSink*s){return s->codec==11?7:s->codec==2?1:0;}
static void xc_sink_class_init(XcSinkClass*k){
 GstElementClass*e=GST_ELEMENT_CLASS(k);GstBaseSinkClass*b=GST_BASE_SINK_CLASS(k);
 gst_element_class_set_static_metadata(e,"XC Amlogic Video Sink","Sink/Video","Encoded IPTV video to native Amlogic decoder","XCEnigma");gst_element_class_add_static_pad_template(e,&pad);
 b->start=start;b->stop=stop;b->set_caps=caps;b->render=render;b->unlock=unlock;b->unlock_stop=unlock_stop;
 g_signal_new_class_handler("get-decoder-time",G_TYPE_FROM_CLASS(k),G_SIGNAL_RUN_LAST|G_SIGNAL_ACTION,G_CALLBACK(decoder_time),NULL,NULL,NULL,G_TYPE_INT64,0);
 g_signal_new_class_handler("get-video-width",G_TYPE_FROM_CLASS(k),G_SIGNAL_RUN_LAST|G_SIGNAL_ACTION,G_CALLBACK(video_width),NULL,NULL,NULL,G_TYPE_INT,0);
 g_signal_new_class_handler("get-video-height",G_TYPE_FROM_CLASS(k),G_SIGNAL_RUN_LAST|G_SIGNAL_ACTION,G_CALLBACK(video_height),NULL,NULL,NULL,G_TYPE_INT,0);
 g_signal_new_class_handler("get-video-framerate",G_TYPE_FROM_CLASS(k),G_SIGNAL_RUN_LAST|G_SIGNAL_ACTION,G_CALLBACK(video_rate),NULL,NULL,NULL,G_TYPE_INT,0);
 g_signal_new_class_handler("get-video-codec",G_TYPE_FROM_CLASS(k),G_SIGNAL_RUN_LAST|G_SIGNAL_ACTION,G_CALLBACK(video_codec),NULL,NULL,NULL,G_TYPE_INT,0);
}
static void xc_sink_init(XcSink*s){s->fd=s->av=s->lockfd=-1;s->fps_n=25;s->fps_d=1;gst_base_sink_set_sync(GST_BASE_SINK(s),TRUE);gst_base_sink_set_async_enabled(GST_BASE_SINK(s),FALSE);gst_base_sink_set_last_sample_enabled(GST_BASE_SINK(s),FALSE);}
static gboolean init(GstPlugin*p){gboolean ok=gst_element_register(p,"xcamlvideosink",GST_RANK_PRIMARY+10,xc_sink_get_type());if(TRUE)ok=ok&&gst_element_register(p,"dreamvideosink",GST_RANK_PRIMARY+10,xc_sink_get_type());return ok;}
GST_PLUGIN_DEFINE(GST_VERSION_MAJOR,GST_VERSION_MINOR,xcamlvideo,"XCEnigma Amlogic native video sink",init,"0.3.0","LGPL",PACKAGE,"https://github.com/3bdlios/gt-panel")
