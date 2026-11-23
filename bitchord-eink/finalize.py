#!/usr/bin/env python3
# Unofficial BitChord e-ink adaptation, GPL-3.0, 2026-11-22.
from pathlib import Path
import re,sys,json
r=Path(sys.argv[1]); changed=[]
def edit(path,fn):
 p=r/path; old=p.read_text(); new=fn(old)
 if new!=old:p.write_text(new);changed.append(path)
A='app/src/main/java/com/music/bitchord/'
S='sharedUi/src/jvmSharedMain/kotlin/com/music/bitchord/'
def welcome(s):
 s=s.replace('    val palette = cyclingMeshPalette(if (page == PAGE_NAME) WelcomeMeshPalettes else ConnectPalettes)','    // E-ink: static paper background; no mesh animation clock.')
 s,n=re.subn(r'        MeshGradientBackground\([\s\S]*?\n        \)\n','',s,count=1);assert n==1
 s=s.replace('Color.White','Color.__INK_SWAP__').replace('Color.Black','Color.White').replace('Color.__INK_SWAP__','Color.Black')
 s=s.replace('modifier = Modifier.size(width = 46.dp, height = 30.dp),','modifier = Modifier.size(width = 46.dp, height = 30.dp),\n                colorFilter = androidx.compose.ui.graphics.ColorFilter.tint(Color.Black),')
 return s
edit(A+'ui/onboarding/OnboardingScreen.kt',welcome)
edit(A+'MainActivity.kt',lambda s:s.replace(' && !onboardingVisible,',','))
def body(s,marker,new):
 start=s.index(marker);at=s.index('{',start);level=1
 pat=re.compile(r'"""[\s\S]*?"""|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*[\s\S]*?\*/|[{}]')
 for m in pat.finditer(s,at+1):
  if m.group()=='{':level+=1
  elif m.group()=='}':level-=1
  if level==0:return s[:at]+'{\n'+new+'\n}'+s[m.end():]
 raise ValueError(marker)
def cards(s):
 s=s.replace('import androidx.compose.foundation.layout.height\n','import androidx.compose.foundation.layout.height\nimport androidx.compose.foundation.layout.heightIn\n',1)
 s=s.replace('import androidx.compose.foundation.background','import androidx.compose.foundation.border\nimport androidx.compose.foundation.background',1)
 s=body(s,'private fun TopPickCard(','''    val text = cardText(pick, listenerName)
    val longPress = onLongPress?.let { { it(pick) } }
    Column(
        modifier = modifier
            .heightIn(min = 112.dp)
            .clip(RoundedCornerShape(2.dp))
            .background(Color.White)
            .border(1.dp, Color.Black, RoundedCornerShape(2.dp))
            .longPressMenuClickable(onClick = { onClick(pick, text.title) }, onLongClick = longPress)
            .contextClick(longPress)
            .padding(12.dp),
        verticalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        Text(text.eyebrow, color = Color.Black, style = MaterialTheme.typography.bodySmall,
            maxLines = 1, overflow = TextOverflow.Ellipsis)
        Text(text.title, color = Color.Black, style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.Bold, maxLines = 3, overflow = TextOverflow.Ellipsis)
        if (text.subtitle.isNotBlank()) {
            Text(text.subtitle, color = Color.Black, style = MaterialTheme.typography.bodyMedium,
                maxLines = 2, overflow = TextOverflow.Ellipsis)
        }
    }''')
 s=s.replace('Modifier.width(cardWidth).aspectRatio(TOP_PICK_RATIO)','Modifier.width(cardWidth).height(112.dp)')
 s=s.replace('val running = LocalArtworkMotion.current','val running = false // E-ink: no decorative frame loop.')
 return s
edit(S+'ui/screens/TopPicksShelf.kt',cards)
# Instant tweens must not be fed into manual infinite animation loops.
edit(A+'ui/components/AudioPipelineDialog.kt',lambda s:s.replace('val isSignalActive = isPlaying && !isReducedMotion','val isSignalActive = false // E-ink: static diagnostic flow.').replace('Color.White','Color.Black').replace('Color(0xFF131315)','Color.White'))
edit(S+'ui/player/MeshGradient.kt',lambda s:s.replace('val reduceAnimation by PlayerSettings.reduceAnimation.collectAsStateWithLifecycle()','val reduceAnimation = true // E-ink: always static.'))
edit(S+'ui/player/PlayerControls.kt',lambda s:s.replace('val crawls = enabled && overflowing','val crawls = false // E-ink: titles remain still.'))
m=r/'EINK-MANIFEST.json';d=json.loads(m.read_text());d['changed']=sorted(set(d['changed']+changed));m.write_text(json.dumps(d,indent=2)+'\n')
print('Static welcome, text cards and safe manual loops:',changed)
