#!/usr/bin/env python3
# Unofficial BitChord e-ink adaptation, GPL-3.0, 2026-11-22.
from pathlib import Path
import re,sys,json
r=Path(sys.argv[1]); changed=[]
def edit(path,fn):
 p=r/path; old=p.read_text(); new=fn(old)
 if new!=old:p.write_text(new);changed.append(path)
A='app/src/main/java/com/music/bitchord/'
def welcome(s):
 s=s.replace('    val palette = cyclingMeshPalette(if (page == PAGE_NAME) WelcomeMeshPalettes else ConnectPalettes)','    // E-ink: static paper background; no mesh animation clock.')
 s,n=re.subn(r'        MeshGradientBackground\([\s\S]*?\n        \)\n','',s,count=1);assert n==1
 s=s.replace('Color.White','Color.__INK_SWAP__').replace('Color.Black','Color.White').replace('Color.__INK_SWAP__','Color.Black')
 s=s.replace('modifier = Modifier.size(width = 46.dp, height = 30.dp),','modifier = Modifier.size(width = 46.dp, height = 30.dp),\n                colorFilter = androidx.compose.ui.graphics.ColorFilter.tint(Color.Black),')
 return s
edit(A+'ui/onboarding/OnboardingScreen.kt',welcome)
edit(A+'MainActivity.kt',lambda s:s.replace(' && !onboardingVisible,',','))
m=r/'EINK-MANIFEST.json';d=json.loads(m.read_text());d['changed']=sorted(set(d['changed']+changed));m.write_text(json.dumps(d,indent=2)+'\n')
print('Static welcome applied:',changed)
