#!/usr/bin/env python3
"""Exercise the actual release APK's power button on API 29. No root/force-stop in exit tests."""
from pathlib import Path
import json, re, subprocess, time, wave, math, struct, hashlib
import xml.etree.ElementTree as ET
OUT=Path('poweroff-results');OUT.mkdir(exist_ok=True)
PKG='com.music.bitchord.eink';ACT=PKG+'/com.music.bitchord.MainActivity'
report={'physical_device_tested':False,'emulator_api':29,'checks':[]}
def adb(*args, check=True, timeout=35):
    p=subprocess.run(['adb',*map(str,args)],capture_output=True,timeout=timeout)
    if check and p.returncode:raise RuntimeError(p.stderr.decode(errors='replace'))
    return p.stdout

def snap(name):
    (OUT/(name+'.png')).write_bytes(adb('exec-out','screencap','-p'))
    adb('shell','uiautomator','dump','/sdcard/power-ui.xml',timeout=25)
    raw=adb('shell','cat','/sdcard/power-ui.xml');(OUT/(name+'.xml')).write_bytes(raw)
    return ET.fromstring(raw)

def tap(root, text=None, desc=None, cls=None):
    for n in root.iter('node'):
        a=n.attrib
        if text is not None and a.get('text','').strip().lower()!=text.lower():continue
        if desc is not None and a.get('content-desc','').strip().lower()!=desc.lower():continue
        if cls is not None and a.get('class')!=cls:continue
        b=list(map(int,re.findall(r'\d+',a.get('bounds',''))))
        if len(b)==4 and b[2]>b[0] and b[3]>b[1]:
            adb('shell','input','tap',(b[0]+b[2])//2,(b[1]+b[3])//2);time.sleep(1);return True
    return False

def ok(name,value,detail=''):
    report['checks'].append({'name':name,'ok':bool(value),'detail':detail})
    print(name, bool(value), detail, flush=True)

def pid():return adb('shell','pidof',PKG,check=False).decode().strip()

def media(name):
    raw=adb('shell','dumpsys','media_session').decode(errors='replace');(OUT/(name+'.txt')).write_text(raw);return raw

def power(root, prefix):
    found=tap(root,desc='Power off BitChord') or tap(root,text='Power off BitChord')
    ok(prefix+' power button accessible',found)
    if not found:raise RuntimeError('Power button not found')
    root=snap(prefix+'-confirm')
    ok(prefix+' confirmation visible',any(n.attrib.get('text')=='Power off BitChord?' for n in root.iter('node')))
    if not tap(root,text='Power off'):raise RuntimeError('Confirm button not found')
    started=time.monotonic()
    while pid() and time.monotonic()-started<22:time.sleep(.5)
    ok(prefix+' process terminated',not pid(),f'observed after {time.monotonic()-started:.1f}s')
    time.sleep(3)
    (OUT/(prefix+'-closed.png')).write_bytes(adb('exec-out','screencap','-p'))
    ok(prefix+' media session removed',PKG not in media(prefix+'-sessions'))
    services=adb('shell','dumpsys','activity','services',PKG).decode(errors='replace')
    (OUT/(prefix+'-services.txt')).write_text(services)
    ok(prefix+' no running app service',not bool(re.search(r'ServiceRecord\{[^\n]*'+re.escape(PKG),services)))
    jobs=adb('shell','dumpsys','jobscheduler').decode(errors='replace');(OUT/(prefix+'-jobs.txt')).write_text(jobs)
    ok(prefix+' no scheduled app jobs',not bool(re.search(r'JOB #[^\n]*'+re.escape(PKG),jobs)))

try:
    adb('logcat','-c');adb('shell','am','start','-W','-n',ACT);time.sleep(8)
    ok('launch',bool(pid()));root=snap('01-welcome')
    if tap(root,cls='android.widget.EditText'):
        adb('shell','input','text','EInkTest');adb('shell','input','keyevent','66');time.sleep(1)
        adb('shell','input','keyevent','4');time.sleep(1)
        root=snap('02-name');ok('setup next',tap(root,text='Next'))
        root=snap('03-connect');ok('skip sign in',tap(root,text='Skip sign in'))
        time.sleep(5)
    root=snap('04-home');ok('home power icon',any(n.attrib.get('content-desc')=='Power off BitChord' for n in root.iter('node')))
    rate=16000;tone=OUT/'Power-Off-Test.wav'
    one=b''.join(struct.pack('<h',int(500*math.sin(2*math.pi*440*n/rate))) for n in range(rate))
    with wave.open(str(tone),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate)
        for _ in range(300):w.writeframesraw(one)
    remote='/sdcard/Android/data/'+PKG+'/files/Power-Off-Test.wav'
    adb('shell','mkdir','-p',remote.rsplit('/',1)[0]);adb('push',tone,remote)
    adb('shell','am','start','-W','-a','android.intent.action.VIEW','-d','file://'+remote,'-t','audio/wav','-n',ACT)
    time.sleep(6);root=snap('05-playing');state=media('playing')
    ok('local audio playing before shutdown',PKG in state and bool(re.search(r'state=3\b',state)))
    adb('shell','input','keyevent','4');time.sleep(2);root=snap('06-player-collapsed')
    original_pid=pid();ok('open power dialog',tap(root,desc='Power off BitChord'))
    root=snap('07-confirm-cancel');ok('cancel available',tap(root,text='Cancel'))
    state=media('after-cancel');ok('cancel leaves same process playing',pid()==original_pid and bool(re.search(r'state=3\b',state)))
    root=snap('08-after-cancel');power(root,'09-first-exit')
    stayed_off=True
    for _ in range(12):
        time.sleep(5)
        if pid():stayed_off=False
    ok('stays terminated for 60 seconds',stayed_off)
    attempted=adb('shell','am','startservice','-n',PKG+'/com.music.bitchord.playback.PlaybackService',check=False)
    (OUT/'stale-start-response.txt').write_bytes(attempted)
    time.sleep(6)
    ok('stale service start does not keep process alive',not pid())
    ok('stale service start does not restore media session',PKG not in media('after-stale-start'))
    adb('shell','am','start','-W','-n',ACT);time.sleep(7);root=snap('10-reopened')
    ok('manual reopening works',bool(pid()))
    ok('onboarding remains completed',any(n.attrib.get('content-desc')=='Power off BitChord' for n in root.iter('node')))
    payload=adb('exec-out','cat',remote)
    ok('saved audio file unchanged',hashlib.sha256(payload).digest()==hashlib.sha256(tone.read_bytes()).digest())
    adb('shell','am','start','-W','-a','android.intent.action.VIEW','-d','file://'+remote,'-t','audio/wav','-n',ACT)
    time.sleep(6);state=media('reopened-playing');ok('playback works after reopening',PKG in state and bool(re.search(r'state=3\b',state)))
    adb('shell','input','keyevent','4');time.sleep(2);root=snap('11-before-second-exit');power(root,'12-second-exit')
except Exception as e:
    report['exception']=repr(e);ok('test completed',False,repr(e))
finally:
    logs=adb('logcat','-d',check=False).decode(errors='replace');(OUT/'logcat.txt').write_text(logs)
    ok('no app fatal exception',not bool(re.search(r'FATAL EXCEPTION[\s\S]{0,600}Process: '+re.escape(PKG),logs)))
    report['all_passed']=all(x['ok'] for x in report['checks']) and 'exception' not in report
    (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
raise SystemExit(0 if report['all_passed'] else 1)
