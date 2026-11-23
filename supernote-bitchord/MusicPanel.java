/* BitChord Notes, experimental Supernote companion plugin. MIT, 2026-11-23. */
package org.bitchord.notes;

import android.content.*;
import android.graphics.Color;
import android.graphics.PixelFormat;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.media.MediaDescription;
import android.media.MediaMetadata;
import android.media.browse.MediaBrowser;
import android.media.session.MediaController;
import android.media.session.MediaSession;
import android.media.session.PlaybackState;
import android.os.*;
import android.provider.Settings;
import android.text.TextUtils;
import android.util.DisplayMetrics;
import android.view.*;
import android.widget.*;
import java.util.*;

/** UI and standard Android media connection shared by the plugin and the test harness.
 * No audio engine, network sockets, note I/O, global gestures or process termination.
 * All methods execute on the main looper. Connections live only while expanded.
 */
public final class MusicPanel {
    public static final String TARGET = "com.music.bitchord.eink";
    private static final String SERVICE = "com.music.bitchord.playback.PlaybackService";
    private final Context context;
    private final WindowManager wm;
    private final Handler main = new Handler(Looper.getMainLooper());
    private LinearLayout root;
    private WindowManager.LayoutParams layout;
    private MediaBrowser browser;
    private MediaController controller;
    private boolean visible, collapsed, registered;
    private int generation, x = 18, y = 110, page, rows = 5;
    private String mode = "now", status = "Not connected", folder = "", folderTitle = "Library", subscribed, stamp = "";
    private final ArrayDeque<Folder> history = new ArrayDeque<>();
    private List<MediaBrowser.MediaItem> items = Collections.emptyList();
    private boolean loading;
    private Runnable timeout;

    private static final class Folder {
        final String id, name; final int page;
        Folder(String id, String name, int page) { this.id=id; this.name=name; this.page=page; }
    }
    public MusicPanel(Context context) {
        this.context = context.getApplicationContext();
        wm = (WindowManager)this.context.getSystemService(Context.WINDOW_SERVICE);
    }
    private int dp(float n) { return Math.round(n * context.getResources().getDisplayMetrics().density); }
    private DisplayMetrics screen() {
        DisplayMetrics d = new DisplayMetrics();
        wm.getDefaultDisplay().getMetrics(d); return d;
    }
    private GradientDrawable outline() {
        GradientDrawable d = new GradientDrawable(); d.setColor(Color.WHITE); d.setStroke(dp(1),Color.BLACK); return d;
    }
    private TextView text(String s, int size, boolean bold) {
        TextView t=new TextView(context); t.setText(s); t.setTextColor(Color.BLACK); t.setTextSize(size);
        t.setFontFeatureSettings("kern"); t.setTypeface(Typeface.DEFAULT,bold?Typeface.BOLD:Typeface.NORMAL);
        t.setPadding(dp(8),dp(5),dp(8),dp(5)); t.setMaxLines(2); t.setEllipsize(TextUtils.TruncateAt.END);
        return t;
    }
    private TextView button(String s, String description, Runnable action) {
        TextView t=text(s,16,true); t.setGravity(Gravity.CENTER); t.setMinHeight(dp(46));
        t.setBackground(outline()); t.setContentDescription(description); t.setFocusable(true);
        t.setClickable(true); t.setOnClickListener(v -> guarded(action)); return t;
    }
    private void guarded(Runnable action) {
        try { action.run(); } catch (Exception e) {
            status="Action unavailable: " + e.getClass().getSimpleName(); render();
            Toast.makeText(context,"Could not complete that action. Open BitChord to check playback.",Toast.LENGTH_LONG).show();
        }
    }
    private LinearLayout row() {
        LinearLayout l=new LinearLayout(context); l.setOrientation(LinearLayout.HORIZONTAL); return l;
    }
    private void add(LinearLayout row, TextView view) {
        LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1);
        p.setMargins(dp(2),dp(2),dp(2),dp(2)); row.addView(view,p);
    }
    private void line(LinearLayout view) {
        root.addView(view,new LinearLayout.LayoutParams(-1,-2));
    }
    public boolean show() {
        if (!Settings.canDrawOverlays(context)) return false;
        if (visible) { if(collapsed)expand(); else hide(); return true; }
        visible=true; collapsed=false; mode="now"; status="Connecting to BitChord…";
        root=new LinearLayout(context); root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(4),dp(4),dp(4),dp(4)); root.setBackground(outline());
        layout=new WindowManager.LayoutParams(dp(340),-2,WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE | WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL,
            PixelFormat.TRANSLUCENT);
        layout.gravity=Gravity.TOP|Gravity.LEFT; layout.x=x; layout.y=y;
        layout.setTitle("BitChord Notes controls");
        try {
            wm.addView(root,layout);
            IntentFilter f=new IntentFilter();f.addAction(Intent.ACTION_CONFIGURATION_CHANGED);f.addAction(Intent.ACTION_SCREEN_OFF);
            if(Build.VERSION.SDK_INT>=33) context.registerReceiver(events,f,Context.RECEIVER_NOT_EXPORTED);
            else context.registerReceiver(events,f);
            registered=true; render(); connect(); return true;
        } catch (Exception e) { hide(); throw e; }
    }
    private final BroadcastReceiver events = new BroadcastReceiver() {
        @Override public void onReceive(Context c, Intent i) {
            if(Intent.ACTION_SCREEN_OFF.equals(i.getAction()))hide();
            else { stamp="";render(); }
        }
    };
    public void hide() {
        visible=false; disconnect();
        if(registered){try{context.unregisterReceiver(events);}catch(Exception ignored){}registered=false;}
        if(root!=null){try{wm.removeViewImmediate(root);}catch(Exception ignored){}root=null;}
        layout=null; stamp=""; items=Collections.emptyList(); history.clear();
    }
    private void minimize() { collapsed=true; disconnect(); stamp=""; render(); }
    private void expand() { collapsed=false; mode="now"; stamp=""; render();connect(); }
    public void openApp() {
        hide(); Intent i=new Intent(Intent.ACTION_MAIN).setComponent(new ComponentName(TARGET,"com.music.bitchord.MainActivity"));
        i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);context.startActivity(i);
    }
    public void powerOff() {
        // Release the foreign service binding BEFORE the target's shutdown. Never kill PluginHost.
        hide(); Intent i=new Intent().setComponent(new ComponentName(TARGET,"com.music.bitchord.EInkPluginPowerActivity"));
        i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        try { context.startActivity(i); }
        catch (ActivityNotFoundException e) {
            openApp();Toast.makeText(context,"Update to the beta3 companion for plugin power off. In beta2, use the app's power button.",Toast.LENGTH_LONG).show();
        }
    }
    private void cancelTimeout(){if(timeout!=null){main.removeCallbacks(timeout);timeout=null;}}
    private void disconnect() {
        generation++;cancelTimeout();
        if(controller!=null){try{controller.unregisterCallback(callback);}catch(Exception ignored){}controller=null;}
        if(browser!=null){try{browser.disconnect();}catch(Exception ignored){}browser=null;}
        subscribed=null;loading=false;
    }
    private void connect() {
        disconnect();if(!visible||collapsed)return;
        status="Connecting to BitChord…";render(); final int g=generation;
        browser=new MediaBrowser(context,new ComponentName(TARGET,SERVICE),new MediaBrowser.ConnectionCallback(){
            @Override public void onConnected(){
                if(g!=generation||browser==null)return;cancelTimeout();
                guarded(() -> {
                    controller=new MediaController(context,browser.getSessionToken());
                    controller.registerCallback(callback,main);status="Connected";render();
                });
            }
            @Override public void onConnectionFailed(){failed(g,"Open BitChord, then reopen this plugin.");}
            @Override public void onConnectionSuspended(){failed(g,"BitChord disconnected. Tap Reconnect.");}
        },null);
        timeout=() -> {if(g==generation){disconnect();status="Connection timed out. Open BitChord first.";render();}};
        main.postDelayed(timeout,12000);
        try{browser.connect();}catch(Exception e){failed(g,"BitChord is unavailable. Install/open the companion app.");}
    }
    private void failed(int g,String message){if(g!=generation)return;disconnect();status=message;render();}
    private final MediaController.Callback callback=new MediaController.Callback(){
        @Override public void onPlaybackStateChanged(PlaybackState state){render();}
        @Override public void onMetadataChanged(MediaMetadata metadata){render();}
        @Override public void onQueueChanged(List<MediaSession.QueueItem> q){render();}
        @Override public void onSessionDestroyed(){disconnect();status="BitChord stopped. Open the app to restart.";render();}
    };
    private String str(CharSequence s){return s==null?"":s.toString();}
    private String title(){MediaMetadata m=controller==null?null:controller.getMetadata();return m==null?"No track selected":str(m.getText(MediaMetadata.METADATA_KEY_TITLE));}
    private String artist(){MediaMetadata m=controller==null?null:controller.getMetadata();return m==null?"":str(m.getText(MediaMetadata.METADATA_KEY_ARTIST));}
    private boolean playing(){PlaybackState s=controller==null?null:controller.getPlaybackState();return s!=null&&(s.getState()==PlaybackState.STATE_PLAYING||s.getState()==PlaybackState.STATE_BUFFERING||s.getState()==PlaybackState.STATE_CONNECTING);}
    private boolean allows(long a){PlaybackState s=controller==null?null:controller.getPlaybackState();return s!=null&&(s.getActions()&a)!=0;}
    private TextView transport(String label,String description,long a,Runnable command){
        TextView t=button(label,description,command);boolean ok=allows(a);t.setEnabled(ok);if(!ok)t.setTextColor(Color.DKGRAY);return t;
    }
    private void folder(String id,String name,int n){
        if(browser==null||!browser.isConnected())return;
        if(subscribed!=null)browser.unsubscribe(subscribed);
        subscribed=id;folder=id;folderTitle=name;page=Math.max(0,n);mode="library";items=Collections.emptyList();loading=true;stamp="";render();
        Bundle o=new Bundle();o.putInt(MediaBrowser.EXTRA_PAGE,page);o.putInt(MediaBrowser.EXTRA_PAGE_SIZE,rows);
        final int g=generation,requested=page;final String expected=id;
        browser.subscribe(id,o,new MediaBrowser.SubscriptionCallback(){
            @Override public void onChildrenLoaded(String p,List<MediaBrowser.MediaItem> list,Bundle options){loaded(list);}
            @Override public void onChildrenLoaded(String p,List<MediaBrowser.MediaItem> list){loaded(list);}
            private void loaded(List<MediaBrowser.MediaItem> list){
                if(g!=generation||!expected.equals(folder)||requested!=page||!"library".equals(mode))return;
                // Bound what is retained/displayed even when a provider ignores paging hints.
                items=new ArrayList<>(list.subList(0,Math.min(rows,list.size())));loading=false;stamp="";render();
            }
            @Override public void onError(String p,Bundle options){error();}
            @Override public void onError(String p){error();}
            private void error(){if(g==generation&&expected.equals(folder)&&requested==page){loading=false;items=Collections.emptyList();status="Library unavailable; open BitChord to sign in or retry.";stamp="";render();}}
        });
    }
    private void library(){history.clear();if(browser!=null&&browser.isConnected())folder(browser.getRoot(),"Library",0);else connect();}
    private void backFolder(){if(history.isEmpty()){mode="now";render();}else{Folder f=history.pop();folder(f.id,f.name,f.page);}}
    private List<MediaSession.QueueItem> queue(){List<MediaSession.QueueItem> q=controller==null?null:controller.getQueue();return q==null?Collections.emptyList():q;}
    private void clamp(){
        if(root==null||layout==null)return;DisplayMetrics d=screen();
        int w=collapsed?dp(62):Math.min(dp(340),d.widthPixels-dp(16));layout.width=w;
        root.measure(View.MeasureSpec.makeMeasureSpec(w,View.MeasureSpec.EXACTLY),View.MeasureSpec.makeMeasureSpec(d.heightPixels,View.MeasureSpec.AT_MOST));
        layout.x=Math.max(0,Math.min(layout.x,Math.max(0,d.widthPixels-w)));
        layout.y=Math.max(0,Math.min(layout.y,Math.max(0,d.heightPixels-root.getMeasuredHeight()-dp(28))));
        x=layout.x;y=layout.y;wm.updateViewLayout(root,layout);
    }
    private void drag(TextView handle,boolean tapExpand){
        handle.setOnTouchListener(new View.OnTouchListener(){float sx,sy;int ox,oy;boolean moved;
            @Override public boolean onTouch(View v,android.view.MotionEvent e){
                if(layout==null)return true;
                switch(e.getActionMasked()){
                    case android.view.MotionEvent.ACTION_DOWN:sx=e.getRawX();sy=e.getRawY();ox=layout.x;oy=layout.y;moved=false;return true;
                    case android.view.MotionEvent.ACTION_MOVE:
                        float dx=e.getRawX()-sx,dy=e.getRawY()-sy;
                        if(Math.abs(dx)+Math.abs(dy)>dp(7))moved=true;
                        if(moved){layout.x=ox+(int)dx;layout.y=oy+(int)dy;clamp();}return true;
                    case android.view.MotionEvent.ACTION_UP:if(!moved&&tapExpand)expand();return true;
                    case android.view.MotionEvent.ACTION_CANCEL:return true;
                    default:return true;
                }
            }
        });
    }
    private void render(){
        if(!visible||root==null)return;
        DisplayMetrics dm=screen();rows=Math.max(2,Math.min(5,(int)(dm.heightPixels/dm.density-260)/48));
        List<MediaSession.QueueItem> q="queue".equals(mode)?queue():Collections.emptyList();
        String key=collapsed+"|"+mode+"|"+status+"|"+title()+"|"+artist()+"|"+playing()+"|"+(controller==null)+"|"+page+"|"+folder+"|"+loading+"|"+q.toString()+"|"+dm.widthPixels+"|"+dm.heightPixels;
        if(key.equals(stamp))return;stamp=key;root.removeAllViews();
        if(collapsed){TextView bubble=button("BC","Expand BitChord controls",this::expand);drag(bubble,true);root.addView(bubble);clamp();return;}
        LinearLayout h=row();TextView handle=text("BitChord Notes",17,true);handle.setContentDescription("Drag controls");drag(handle,false);
        h.addView(handle,new LinearLayout.LayoutParams(0,dp(44),1));
        TextView min=button("−","Minimize controls",this::minimize),close=button("×","Hide controls",this::hide);
        h.addView(min,new LinearLayout.LayoutParams(dp(44),dp(44)));h.addView(close,new LinearLayout.LayoutParams(dp(44),dp(44)));line(h);
        if("now".equals(mode)){
            root.addView(text(title(),19,true));if(!artist().isEmpty())root.addView(text(artist(),15,false));
            root.addView(text(controller==null?status:(playing()?"Playing":"Paused / ready"),14,false));
            if(controller!=null){
                LinearLayout r=row();
                add(r,transport("Previous","Previous track",PlaybackState.ACTION_SKIP_TO_PREVIOUS,() -> controller.getTransportControls().skipToPrevious()));
                boolean p=playing();
                add(r,transport(p?"Pause":"Play",p?"Pause music":"Play music",p?PlaybackState.ACTION_PAUSE:PlaybackState.ACTION_PLAY,() -> {if(playing())controller.getTransportControls().pause();else controller.getTransportControls().play();}));
                add(r,transport("Next","Next track",PlaybackState.ACTION_SKIP_TO_NEXT,() -> controller.getTransportControls().skipToNext()));line(r);
                r=row();add(r,button("Library","Browse library",this::library));add(r,button("Queue","Show queue",() -> {mode="queue";page=0;render();}));line(r);
                r=row();add(r,button("Vol −","Lower music volume",() -> controller.adjustVolume(-1,0)));add(r,button("Vol +","Raise music volume",() -> controller.adjustVolume(1,0)));add(r,button("Full app","Open full BitChord app",this::openApp));line(r);
            }else{
                LinearLayout r=row();add(r,button("Open BitChord","Open full BitChord app",this::openApp));add(r,button("Reconnect","Reconnect to BitChord",this::connect));line(r);
            }
        }else{
            LinearLayout r=row();add(r,button("Back","Back to parent",() -> {if("queue".equals(mode)){mode="now";render();}else backFolder();}));add(r,button("Player","Return to player",() -> {mode="now";render();}));line(r);
            root.addView(text("queue".equals(mode)?"Queue":folderTitle,18,true));
            if("queue".equals(mode)){
                if(q.isEmpty())root.addView(text("The player has no exposed queue.",15,false));
                int end=Math.min(q.size(),(page+1)*rows);
                for(int k=page*rows;k<end;k++){
                    MediaSession.QueueItem item=q.get(k);root.addView(button(str(item.getDescription().getTitle()),"Play queue item "+str(item.getDescription().getTitle()),() -> {if(controller!=null)controller.getTransportControls().skipToQueueItem(item.getQueueId());mode="now";render();}));
                }
            }else if(loading){root.addView(text("Loading…",16,false));}
            else if(items.isEmpty()){root.addView(text("No entries on this page. Use Back or open BitChord.",15,false));}
            else for(MediaBrowser.MediaItem item:items){
                MediaDescription d=item.getDescription();String name=str(d.getTitle());
                TextView b=button((item.isBrowsable()?"> ":"")+name,name,() -> {
                    if(item.isBrowsable()){history.push(new Folder(folder,folderTitle,page));folder(item.getMediaId(),name,0);}
                    else if(item.isPlayable()&&controller!=null){controller.getTransportControls().playFromMediaId(item.getMediaId(),d.getExtras());mode="now";render();}
                });b.setMaxLines(2);b.setEnabled(item.isBrowsable()||item.isPlayable());root.addView(b);
            }
            r=row();TextView prev=button("< Page","Previous page",() -> {if("queue".equals(mode)){page=Math.max(0,page-1);render();}else folder(folder,folderTitle,page-1);});prev.setEnabled(page>0);add(r,prev);
            TextView next=button("Page >","Next page",() -> {if("queue".equals(mode)){page++;render();}else folder(folder,folderTitle,page+1);});next.setEnabled("queue".equals(mode)?q.size()>(page+1)*rows:!loading&&items.size()>=rows);add(r,next);line(r);
        }
        TextView power=button("Power off BitChord","Power off BitChord",this::powerOff);root.addView(power);
        root.addView(text("× hides controls; music keeps playing.",12,false));clamp();
    }
}
