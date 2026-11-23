#!/usr/bin/env python3
"""Create BitChord Notes plugin project; MIT. Inputs are pinned official npm template and SDK."""
from pathlib import Path
import sys,json,shutil,tarfile,struct,zlib
here=Path(__file__).parent;r=Path(sys.argv[1]);r.mkdir(parents=True,exist_ok=True)
def put(p,s):
 p=r/p;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s)
pkg={'name':'BitChordNotes','version':'0.1.0','private':True,'description':'Unofficial floating BitChord controller for Supernote notes','dependencies':{'react':'19.0.0','react-native':'0.79.2','sn-plugin-lib':'0.2.3'},'devDependencies':{'@babel/core':'^7.25.2','@babel/runtime':'^7.25.0','@react-native-community/cli':'18.0.0','@react-native-community/cli-platform-android':'18.0.0','@react-native/babel-preset':'0.79.2','@react-native/metro-config':'0.79.2'}}
put('package.json',json.dumps(pkg,indent=2)+'\n')
put('app.json',json.dumps({'name':'BitChordNotes','displayName':'BitChord Notes'}))
put('babel.config.js',"module.exports={presets:['module:@react-native/babel-preset']};\n")
put('metro.config.js',"const {getDefaultConfig,mergeConfig}=require('@react-native/metro-config'); module.exports=mergeConfig(getDefaultConfig(__dirname),{resolver:{useWatchman:false}});\n")
put('react-native.config.js',"module.exports={project:{android:{sourceDir:'./android'}}};\n")
put('index.js','''import React, {useState} from 'react';
import {AppRegistry, Image, NativeModules, Text, View, Pressable} from 'react-native';
import {PluginManager} from 'sn-plugin-lib';
const bridge=NativeModules.BitChordNotes;
let lastError='Open the floating controls from your note toolbar.';
function App(){
 const [error,setError]=useState(lastError);
 const act=async(fn)=>{try{if(!bridge)throw Error('Native plugin module is unavailable. Reinstall the complete .snplg package.');await fn();}catch(e){setError(String(e.message||e));}};
 const b=(label,fn)=>React.createElement(Pressable,{onPress:()=>act(fn),style:{borderColor:'#000',borderWidth:2,padding:18,marginVertical:8}},React.createElement(Text,{style:{color:'#000',fontSize:20}},label));
 return React.createElement(View,{style:{flex:1,backgroundColor:'#fff',padding:28,justifyContent:'center'}},
  React.createElement(Text,{style:{fontSize:28,color:'#000',fontWeight:'bold'}},'BitChord Notes'),
  React.createElement(Text,{style:{fontSize:19,color:'#000',marginVertical:20}},error),
  React.createElement(Text,{style:{fontSize:17,color:'#000'}},'This plugin uses your BitChord E-Ink app for music. Floating windows must be permitted for Supernote PluginHost. No access to your notes is requested.'),
  b('Show floating controls',async()=>{await bridge.open();await PluginManager.closePluginView();}),
  b('Open BitChord',async()=>{await bridge.openApp();await PluginManager.closePluginView();}),
  b('Close',async()=>{if(bridge)await bridge.hide();await PluginManager.closePluginView();}));
}
AppRegistry.registerComponent('BitChordNotes',()=>App);
(async()=>{
 await PluginManager.init();
 if(bridge)await bridge.hide();
 PluginManager.registerPluginLifeListener({onMsg:event=>{if(event?.state===4||event?.state===5){bridge?.hide().catch(()=>{});}}});
 PluginManager.registerButtonListener({onButtonPress:async event=>{
  if(event.id!==61301)return;
  try{if(!bridge)throw Error('Native plugin module is unavailable. Reinstall the complete plugin package.');await bridge.open();}
  catch(e){lastError=String(e.message||e);await PluginManager.showPluginView();}
 }});
 await PluginManager.registerButton(1,['NOTE','DOC'],{id:61301,name:'BitChord Notes',icon:Image.resolveAssetSource(require('./assets/icon.png')).uri,showType:0});
})().catch(e=>{lastError='Plugin startup failed: '+String(e.message||e);console.error(lastError);});
''')
put('android/settings.gradle', '''pluginManagement { repositories { google(); mavenCentral(); gradlePluginPortal() } }
dependencyResolutionManagement { repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS); repositories { google(); mavenCentral() } }
rootProject.name='BitChordNotesNative'
include ':app'
''')
put('android/build.gradle',"plugins { id 'com.android.application' version '8.10.1' apply false }\n")
put('android/gradle.properties','android.useAndroidX=true\norg.gradle.jvmargs=-Xmx2g -Dfile.encoding=UTF-8\n')
put('android/app/build.gradle','''plugins { id 'com.android.application' }
android {
 namespace 'org.bitchord.notes'
 compileSdk 35
 defaultConfig { applicationId 'org.bitchord.notes.nativecode'; minSdk 27; targetSdk 35; versionCode 1; versionName '0.1.0' }
 compileOptions { sourceCompatibility JavaVersion.VERSION_17; targetCompatibility JavaVersion.VERSION_17 }
 buildTypes { release { minifyEnabled false }; debug { applicationIdSuffix '.harness' } }
 aaptOptions { additionalParameters '--allow-reserved-package-id', '--package-id', '0x6f' }
}
dependencies { compileOnly 'com.facebook.react:react-android:0.79.2' }
''')
put('android/app/src/main/AndroidManifest.xml','''<manifest xmlns:android="http://schemas.android.com/apk/res/android">
<uses-permission android:name="android.permission.SYSTEM_ALERT_WINDOW" />
<queries><package android:name="com.music.bitchord.eink" /></queries>
<application android:label="BitChord Notes native module" android:allowBackup="false" android:theme="@android:style/Theme.Material.Light.NoActionBar" />
</manifest>''')
put('android/app/src/debug/AndroidManifest.xml','''<manifest xmlns:android="http://schemas.android.com/apk/res/android"><application>
<activity android:name="org.bitchord.notes.HarnessActivity" android:exported="true"><intent-filter><action android:name="android.intent.action.MAIN"/><category android:name="android.intent.category.LAUNCHER"/></intent-filter></activity>
</application></manifest>''')
put('android/app/src/debug/java/org/bitchord/notes/HarnessActivity.java','''package org.bitchord.notes;
import android.app.Activity;import android.os.Bundle;import android.content.Intent;import android.provider.Settings;import android.net.Uri;import android.widget.*;
/** Emulator test driver only; not packaged in the plugin's release native module. */
public class HarnessActivity extends Activity {
 private MusicPanel panel;
 @Override public void onCreate(Bundle b){super.onCreate(b);panel=new MusicPanel(this);
 LinearLayout v=new LinearLayout(this);v.setOrientation(1);v.setPadding(24,24,24,24);
 TextView t=new TextView(this);t.setText("TEST HARNESS — NOT SUPERN0TE\nThe same MusicPanel class is used in the plugin. Native note integration is not simulated here.");v.addView(t);
 Button show=new Button(this);show.setText("Show controls");show.setOnClickListener(w->{if(!panel.show())startActivity(new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,Uri.parse("package:"+getPackageName())));});v.addView(show);setContentView(v);}
 @Override public void onDestroy(){if(panel!=null)panel.hide();super.onDestroy();}
}
''')
put('android/app/src/main/java/org/bitchord/notes/NotesPackage.java','''package org.bitchord.notes;
import com.facebook.react.ReactPackage;import com.facebook.react.bridge.*;import com.facebook.react.uimanager.ViewManager;import java.util.*;
public final class NotesPackage implements ReactPackage {
 public List<NativeModule> createNativeModules(ReactApplicationContext c){return Collections.singletonList(new NotesModule(c));}
 public List<ViewManager> createViewManagers(ReactApplicationContext c){return Collections.emptyList();}
}
''')
put('android/app/src/main/java/org/bitchord/notes/NotesModule.java','''package org.bitchord.notes;
import com.facebook.react.bridge.*;import android.os.*;
public final class NotesModule extends ReactContextBaseJavaModule {
 private final MusicPanel panel;private final Handler main=new Handler(Looper.getMainLooper());
 public NotesModule(ReactApplicationContext c){super(c);panel=new MusicPanel(c);}
 @Override public String getName(){return "BitChordNotes";}
 @ReactMethod public void open(Promise p){main.post(()->{try{if(panel.show())p.resolve(true);else p.reject("OVERLAY_DENIED","Floating windows are not allowed for Supernote PluginHost on this device. Enable its overlay permission in system settings where available.");}catch(Exception e){p.reject("PANEL_FAILED",e);}});}
 @ReactMethod public void hide(Promise p){main.post(()->{panel.hide();p.resolve(true);});}
 @ReactMethod public void openApp(Promise p){main.post(()->{try{panel.openApp();p.resolve(true);}catch(Exception e){p.reject("NO_COMPANION","Install the BitChord E-Ink companion APK first.",e);}});}
 @Override public void invalidate(){main.post(panel::hide);super.invalidate();}
}
''')
put('android/app/src/main/java/org/bitchord/notes/MusicPanel.java',(here/'MusicPanel.java').read_text())
# Official template wrapper only; no bundled sample application or private credentials.
with tarfile.open(sys.argv[2]) as t:
 for member in t.getmembers():
  prefix='package/template/android/'
  if member.isfile() and member.name.startswith(prefix):
   name=member.name[len(prefix):]
   if name in ('gradlew','gradlew.bat','gradle/wrapper/gradle-wrapper.properties','gradle/wrapper/gradle-wrapper.jar'):
    dst=r/'android'/name;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(t.extractfile(member).read())
(r/'android/gradlew').chmod(0o755)
# Small black music-note glyph, generated without any font files.
w=h=96;raw=bytearray()
for y in range(h):
 raw.append(0)
 for x in range(w):
  black=(31<=x<=37 and 19<=y<=70) or (68<=x<=74 and 12<=y<=62) or (31<=x<=74 and 12+(74-x)//6<=y<=21+(74-x)//6) or ((x-25)**2/160+(y-70)**2/65<=1) or ((x-62)**2/160+(y-62)**2/65<=1)
  raw.extend(bytes([0 if black else 255])*3)
def chunk(t,b):return struct.pack('>I',len(b))+t+b+struct.pack('>I',zlib.crc32(t+b)&0xffffffff)
icon=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(bytes(raw)))+chunk(b'IEND',b'')
(r/'assets').mkdir(exist_ok=True);(r/'assets/icon.png').write_bytes(icon)
put('PluginConfig.json',json.dumps({'name':'BitChord Notes','pluginKey':'BitChordNotes','pluginID':'bcn0tes23nov2026a','iconPath':'/icon.png','desc':'Unofficial floating controls for BitChord E-Ink. Requires companion APK. Does not read or modify notes.','versionCode':'1','versionName':'0.1.0-experimental','jsMainPath':'index','nativeCodePackage':'/app.npk','reactPackages':['org.bitchord.notes.NotesPackage'],'uses-permissions':[],'author':'Unofficial personal-use experiment'},indent=2)+'\n')
put('LICENSE','''MIT License

Copyright (c) 2026 BitChord Notes contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
''')
put('THIRD-PARTY-NOTICES.txt','''Bundled JavaScript dependencies: React 19.0.0, React Native 0.79.2 (Meta Platforms, MIT), and sn-plugin-lib 0.2.3 (Ratta, MIT). Exact transitive dependencies appear in package-lock.json. Their included license files are retained under licenses/ by the build. Android framework and React Native runtime native classes are provided by the device/PluginHost and not bundled in app.npk. The separate BitChord E-Ink companion remains GPL-3.0 with corresponding source supplied separately.\n''')
print('Prepared official-SDK plugin project',r)
