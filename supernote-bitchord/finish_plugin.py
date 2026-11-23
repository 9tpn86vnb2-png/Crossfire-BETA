#!/usr/bin/env python3
"""Finalize the generated project for the existing beta2 companion; MIT."""
from pathlib import Path
import sys
r=Path(sys.argv[1]);p=r/'android/app/src/main/java/org/bitchord/notes/MusicPanel.java';s=p.read_text()
a=s.index('    public void powerOff() {');b=s.index('    private void cancelTimeout()',a)
s=s[:a]+'''    public void powerOff() {
        // Existing beta2 has no external shutdown API. Hide/unbind this panel and
        // hand the user to its own confirmation UI rather than kill PluginHost.
        openApp();
        Toast.makeText(context,"In BitChord, tap the power icon and confirm Power off. These floating controls are now closed.",Toast.LENGTH_LONG).show();
    }
'''+s[b:]
s=s.replace('button("Power off BitChord","Power off BitChord",this::powerOff)', 'button("Power off via app…","Power off via app",this::powerOff)')
p.write_text(s)
p=r/'android/app/src/debug/java/org/bitchord/notes/HarnessActivity.java';s=p.read_text().replace('SUPERN0TE\nThe same','SUPERNOTE - The same');p.write_text(s)
p=r/'index.js';s=p.read_text()
s=s.replace("const bridge=NativeModules.BitChordNotes;", "const bridge=NativeModules.BitChordNotes;\nconst needBridge=()=>{if(!bridge)throw Error('Native plugin module is unavailable. Reinstall the complete .snplg package.');return bridge;};")
s=s.replace("try{if(!bridge)throw Error('Native plugin module is unavailable. Reinstall the complete .snplg package.');await fn();}", "try{await fn();}")
s=s.replace("await bridge.open();await PluginManager.closePluginView();", "await needBridge().open();await PluginManager.closePluginView();")
s=s.replace("await bridge.openApp();await PluginManager.closePluginView();", "await needBridge().openApp();await PluginManager.closePluginView();")
s=s.replace("if(bridge)await bridge.hide();\n PluginManager.registerPluginLifeListener", "if(bridge)await bridge.hide().catch(()=>{});\n PluginManager.registerPluginLifeListener")
p.write_text(s)
(r/'COMPATIBILITY.md').write_text('''# Compatibility\n\nThis plugin uses the already-installed com.music.bitchord.eink beta2 APK. No APK\nreplacement or uninstall is needed. The power action closes/unbinds the panel\nand opens BitChord; tap that app's power icon and confirm Power off. It does not\nsilently stop playback, nor claim to offer direct remote process termination.\n\nFull search, sign-in and settings remain in the existing app. This release\nprovides an in-note controller plus the library exposed by MediaBrowser.\n\nThe prototype beta3 companion bridge is not included: its signing-key restore\nfailed, so it was deliberately not rebuilt with a different key.\n''')
print('Finalized controller for unchanged beta2 companion; shutdown handoff is explicit')
