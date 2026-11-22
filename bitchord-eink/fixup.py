#!/usr/bin/env python3
# Unofficial BitChord e-ink adaptation, GPL-3.0, 2026-11-22.
from pathlib import Path
import re,sys,json
r=Path(sys.argv[1]); changed=[]
def edit(p,f):
 p=r/p; old=p.read_text(); new=f(old)
 if new!=old:p.write_text(new);changed.append(str(p.relative_to(r)))
A=Path('app/src/main/java/com/music/bitchord')
S=Path('sharedUi/src/jvmSharedMain/kotlin/com/music/bitchord')
edit(S/'ui/components/Skeletons.kt',lambda s:s.replace('import androidx.compose.foundation.layout.Arrangement','import androidx.compose.foundation.background\nimport androidx.compose.foundation.layout.Arrangement'))
for p in (r/'app/src/main/res').rglob('*.xml'):
 edit(p.relative_to(r),lambda s:re.sub(r'@font/sf_pro_display_\w+','sans-serif',s))
edit(Path('wearos/src/main/java/com/music/bitchord/wear/ui/Theme.kt'),lambda s:re.sub(r'val SFPro = FontFamily\([\s\S]*?\n\)', 'val SFPro = FontFamily.SansSerif',s,count=1))
# Holding recurring visual animation values does not register a frame clock.
# In particular, an infinite repeat of a zero-duration tween must never run.
for folder in [r/A/'ui',r/S/'ui']:
 for p in folder.rglob('*.kt'):
  if 'eink' in p.parts:continue
  edit(p.relative_to(r),lambda s:s.replace('import androidx.compose.animation.core.rememberInfiniteTransition\n','import com.music.bitchord.ui.eink.rememberInkInfiniteTransition as rememberInfiniteTransition\n'))
edit(S/'ui/eink/EInkUi.kt',lambda s:s+'''
/** Static replacement for decorative infinite float transitions. */
class InkInfiniteTransition {
    @Composable
    @Suppress("UNUSED_PARAMETER")
    fun animateFloat(
        initialValue: Float,
        targetValue: Float,
        animationSpec: androidx.compose.animation.core.InfiniteRepeatableSpec<Float>,
        label: String = "",
    ): androidx.compose.runtime.State<Float> =
        androidx.compose.runtime.remember(initialValue) {
            androidx.compose.runtime.mutableStateOf(initialValue)
        }
}
@Composable
@Suppress("UNUSED_PARAMETER")
fun rememberInkInfiniteTransition(label: String = ""): InkInfiniteTransition =
    androidx.compose.runtime.remember { InkInfiniteTransition() }
''')
# Full-bleed header luminance must not independently fetch a discarded image.
edit(S/'ui/theme/ArtworkPalette.kt',lambda s:s.replace('): Float? = rememberArtworkSeed(imageUrl, artPx)?.topBandLuminance','): Float? = 1f'))
m=r/'EINK-MANIFEST.json';data=json.loads(m.read_text());data['changed']=sorted(set(data['changed']+changed));m.write_text(json.dumps(data,indent=2)+'\n')
for folder in [r/'app/src',r/'wearos/src',r/'sharedUi/src/jvmSharedMain']:
 for p in folder.rglob('*'):
  if p.is_file() and p.suffix in {'.kt','.xml'}:
   t=p.read_text();assert not re.search(r'(R|Res)\.font\.|@font/',t),str(p)
print('E-ink follow-up checks passed:',len(changed),'files')
