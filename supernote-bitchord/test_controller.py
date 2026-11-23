#!/usr/bin/env python3
"""Test the exact native controller on API29, not Supernote PluginHost. MIT."""
from pathlib import Path
import subprocess,time,re,json,xml.etree.ElementTree as ET,wave,struct,math,hashlib,sys
OUT=Path('plugin-tests');OUT.mkdir(exist_ok=True)
PKG='com.music.bitchord.eink';ACT=PKG+'/com.music.bitchord.MainActivity'
HAR='org.bitchord.notes.nativecode.harness';HACT=HAR+'/org.bitchord.notes.HarnessActivity'
report={'physical_supernote_tested':False,'supernote_pluginhost_tested':False,'scope':'same native MusicPanel class in an Android API29 test harness, existing beta2 APK','checks':[]}
def adb(*a,check=True,timeout=40):
 p=subprocess.run(['adb',*map(str,a)],capture_output=True,timeout=timeout)
 if check and p.returncode:raise RuntimeError((p.stdout+p.stderr).decode(errors='replace'))
 return p.stdout
def ck(n,ok,d=''):
 report['checks'].append({'name':n,'ok':bool(ok),'detail':d});print(n,ok,flush=True);return bool(ok)
def snap(name):
 (OUT/(name+'.png')).write_bytes(adb('exec-out','screencap','-p'))
 adb('shell','uiautomator','dump','/sdcard/plugin-ui.xml',timeout=30)
 b=adb('shell','cat','/sdcard/plugin-ui.xml');(OUT/(name+'.xml')).write_bytes(b);return ET.fromstring(b)
def tap(root,label,desc=False):
 key='content-desc' if desc else 'text'
 for n in root.iter('node'):
  if n.get(key,'').strip().lower()!=label.lower():continue
  b=list(map(int,re.findall(r'\d+',n.get('bounds',''))))
  if len(b)==4 and b[2]>b[0] and b[3]>b[1] and n.get('enabled')!='false':
   adb('shell','input','tap',(b[0]+b[2])//2,(b[1]+b[3])//2);time.sleep(2);return True
 return False
def has(root,s):return any(s.lower() in (n.get('text','')+' '+n.get('content-desc','')).lower() for n in root.iter('node'))
def pid(pkg):return adb('shell','pidof',pkg,check=False).decode().strip()
def media(name):
 s=adb('shell','dumpsys','media_session').decode(errors='replace');(OUT/(name+'.txt')).write_text(s)
 # Historical media-button receivers are not actual media session records.
 m=re.search(r'(?m)^\s*package='+re.escape(PKG)+r'\s*$',s)
 if not m:return None
 tail=s[m.end():];p=re.search(r'state=PlaybackState\s*\{state=(\d+)',tail)
 if not p:p=re.search(r'state=(\d+)\b',tail)
 return int(p.group(1)) if p else -1
def show(name):
 adb('shell','am','start','-W','-n',HACT);time.sleep(1);r=snap(name+'-harness')
 if not tap(r,'Show controls'):raise RuntimeError('Harness show button unavailable')
 time.sleep(3);return snap(name)
def playing_source():
 adb('shell','am','start','-W','-a','android.intent.action.VIEW','-d','file:///sdcard/Android/data/'+PKG+'/files/Plugin-Test.wav','-t','audio/wav','-n',ACT);time.sleep(7)
try:
 adb('logcat','-c');adb('shell','am','start','-W','-n',ACT);time.sleep(8);r=snap('01-app-setup')
 editors=[n for n in r.iter('node') if n.get('class')=='android.widget.EditText']
 if editors:
  b=list(map(int,re.findall(r'\d+',editors[0].get('bounds',''))));adb('shell','input','tap',(b[0]+b[2])//2,(b[1]+b[3])//2)
  adb('shell','input','text','PluginTest');adb('shell','input','keyevent',66);adb('shell','input','keyevent',4);time.sleep(2)
  r=snap('02-app-name');ck('onboarding next',tap(r,'Next'));r=snap('03-app-connect');ck('skip optional login',tap(r,'Skip sign in'));time.sleep(5)
 tone=OUT/'Plugin-Test.wav';rate=16000
 one=b''.join(struct.pack('<h',int(450*math.sin(2*math.pi*440*n/rate))) for n in range(rate))
 with wave.open(str(tone),'wb') as w:
  w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate)
  for _ in range(300):w.writeframesraw(one)
 adb('shell','mkdir','-p','/sdcard/Android/data/'+PKG+'/files');adb('push',tone,'/sdcard/Android/data/'+PKG+'/files/Plugin-Test.wav')
 playing_source();ck('local playback before controller',media('04-media-before')==3)
 r=show('05-floating-player');ck('native floating panel visible',has(r,'BitChord Notes'));ck('metadata appears',has(r,'Plugin-Test'))
 ck('pause button reachable',tap(r,'Pause music',True));ck('pause reaches companion player',media('06-media-paused')==2)
 r=snap('06-paused');ck('play button reachable',tap(r,'Play music',True));ck('play resumes companion',media('07-media-resumed')==3)
 r=snap('07-playing');ck('library button reachable',tap(r,'Browse library',True));time.sleep(4);r=snap('08-library')
 ck('library root entries received',any(has(r,s) for s in ['Quick Picks','Recents','Playlists','Liked','More']))
 ck('return from library',tap(r,'Return to player',True));r=snap('09-player');ck('queue view reachable',tap(r,'Show queue',True));r=snap('10-queue');ck('queue metadata received',has(r,'Plugin-Test'));tap(r,'Return to player',True)
 r=snap('11-before-volume');before=adb('shell','dumpsys','audio');ck('volume button reachable',tap(r,'Lower music volume',True));after=adb('shell','dumpsys','audio');(OUT/'volume-before.txt').write_bytes(before);(OUT/'volume-after.txt').write_bytes(after)
 r=snap('12-before-minimize');ck('minimize button',tap(r,'Minimize controls',True));r=snap('13-minimized');ck('compact bubble visible',has(r,'Expand BitChord controls'));ck('music survives minimizing',media('13-media')==3)
 ck('expand bubble',tap(r,'Expand BitChord controls',True));time.sleep(2);r=snap('14-expanded');ck('hide button',tap(r,'Hide controls',True));r=snap('15-hidden');ck('overlay removed when hidden',not has(r,'BitChord Notes'));ck('music survives hiding',media('15-media')==3)
 r=show('16-shutdown-handoff');ck('power-off handoff button',tap(r,'Power off via app',True));r=snap('17-existing-app');ck('handoff opens existing app power control',has(r,'Power off BitChord'))
 ck('existing app power confirmation',tap(r,'Power off BitChord',True));r=snap('18-confirmation');ck('cancel remains available',tap(r,'Cancel'));ck('cancel keeps music playing',media('18-cancel-media')==3)
 r=snap('19-before-shutdown');ck('reopen existing confirmation',tap(r,'Power off BitChord',True));r=snap('20-power-confirm');ck('confirm actual shutdown',tap(r,'Power off'))
 deadline=time.time()+30
 while pid(PKG) and time.time()<deadline:time.sleep(1)
 ck('companion process exits',not pid(PKG));ck('controller host process is untouched',bool(pid(HAR)));ck('active companion media session removed',media('21-media-after-shutdown') is None)
 checks=[]
 for _ in range(6):time.sleep(5);checks.append(pid(PKG))
 ck('companion remains absent for thirty seconds',not any(checks),repr(checks));snap('21-after-shutdown')
 playing_source();ck('music works after intentional reopen',media('22-media-after-reopen')==3)
 remote=adb('shell','sha256sum','/sdcard/Android/data/'+PKG+'/files/Plugin-Test.wav').decode();ck('audio file preserved by shutdown',remote.startswith(hashlib.sha256(tone.read_bytes()).hexdigest()))
 r=show('23-final-controller');ck('controller reconnects after reopening music',has(r,'Pause music'))
except Exception as e:report['exception']=repr(e)
finally:
 logs=adb('logcat','-d',check=False).decode(errors='replace');(OUT/'logcat.txt').write_text(logs)
 fatal=bool(re.search(r'FATAL EXCEPTION[\s\S]{0,500}(?:com\.music\.bitchord\.eink|org\.bitchord\.notes\.nativecode\.harness)',logs))
 ck('no target-app fatal exception in captured log',not fatal)
 report['passed']=sum(c['ok'] for c in report['checks']);report['total']=len(report['checks'])
 report['success']=report['passed']==report['total'] and 'exception' not in report
 (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
 sys.exit(0 if report['success'] else 1)
