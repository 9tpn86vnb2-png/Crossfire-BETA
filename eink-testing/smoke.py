#!/usr/bin/env python3
"""API-29 emulator smoke test; no account credentials or online searches."""
from pathlib import Path
import json,re,subprocess,time,wave,math,struct
import xml.etree.ElementTree as ET
OUT=Path('smoke-results');OUT.mkdir(exist_ok=True)
PKG='com.music.bitchord.eink';ACT=PKG+'/com.music.bitchord.MainActivity'
report={'hardware_tested':False,'emulator_api':29,'checks':[]}
def adb(*args,check=True,timeout=40):
 p=subprocess.run(['adb',*map(str,args)],capture_output=True,timeout=timeout)
 if check and p.returncode:raise RuntimeError(p.stderr.decode(errors='replace'))
 return p.stdout
def snapshot(name):
 (OUT/(name+'.png')).write_bytes(adb('exec-out','screencap','-p'))
 try:
  adb('shell','uiautomator','dump','/sdcard/eink-ui.xml',timeout=25)
  raw=adb('shell','cat','/sdcard/eink-ui.xml');(OUT/(name+'.xml')).write_bytes(raw)
  return ET.fromstring(raw)
 except Exception as e:
  report['checks'].append({'name':'ui-dump '+name,'ok':False,'detail':str(e)});return None
def tap_node(root,match):
 if root is None:return False
 for n in root.iter('node'):
  if not match(n.attrib):continue
  b=list(map(int,re.findall(r'\d+',n.attrib.get('bounds',''))))
  if len(b)==4 and b[2]>b[0] and b[3]>b[1]:
   adb('shell','input','tap',(b[0]+b[2])//2,(b[1]+b[3])//2);time.sleep(2);return True
 return False
def checked(name,ok,detail=''):
 report['checks'].append({'name':name,'ok':bool(ok),'detail':detail})
try:
 adb('logcat','-c');adb('shell','am','start','-W','-n',ACT);time.sleep(8)
 checked('process started',bool(adb('shell','pidof',PKG,check=False).strip()))
 root=snapshot('01-welcome')
 edit=tap_node(root,lambda a:a.get('class')=='android.widget.EditText');checked('name field found',edit)
 if edit:
  adb('shell','input','text','EInkTest');adb('shell','input','keyevent','66');time.sleep(1)
  adb('shell','input','keyevent','4');time.sleep(1)
  root=snapshot('02-name-entered')
  checked('onboarding next',tap_node(root,lambda a:a.get('text','').strip().lower()=='next'))
  root=snapshot('03-connect')
  checked('skip sign-in',tap_node(root,lambda a:'skip sign in' in a.get('text','').lower()))
  time.sleep(6);root=snapshot('04-home')
 rate=16000;duration=120;tone=OUT/'EInk-Test.wav'
 one=b''.join(struct.pack('<h',int(600*math.sin(2*math.pi*440*n/rate))) for n in range(rate))
 with wave.open(str(tone),'wb') as w:
  w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate)
  for _ in range(duration):w.writeframesraw(one)
 adb('shell','mkdir','-p','/sdcard/Music');adb('push',tone,'/sdcard/Music/EInk-Test.wav')
 adb('shell','am','start','-W','-a','android.intent.action.VIEW','-d','file:///sdcard/Music/EInk-Test.wav','-t','audio/wav','-n',ACT)
 time.sleep(7);root=snapshot('05-local-player')
 media=adb('shell','dumpsys','media_session').decode(errors='replace');(OUT/'media-session.txt').write_text(media)
 checked('media session exists',PKG in media)
 checked('playing state observed',PKG in media and bool(re.search(r'state=3\b',media)))
 checked('pause control reachable',tap_node(root,lambda a:a.get('content-desc','').strip().lower() in {'pause','pause playback'}))
 snapshot('06-paused');adb('shell','input','keyevent','4');time.sleep(1);root=snapshot('07-navigation')
 checked('search screen reachable',tap_node(root,lambda a:a.get('text','').strip().lower()=='search' or a.get('content-desc','').strip().lower()=='search'))
 snapshot('08-search');checked('process survives interactions',bool(adb('shell','pidof',PKG,check=False).strip()))
except Exception as e:report['exception']=repr(e)
finally:
 (OUT/'logcat.txt').write_bytes(adb('logcat','-d',check=False));logs=(OUT/'logcat.txt').read_text(errors='replace')
 checked('no app fatal exception observed',not bool(re.search(r'FATAL EXCEPTION[\s\S]{0,400}com\.music\.bitchord\.eink',logs)))
 (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
