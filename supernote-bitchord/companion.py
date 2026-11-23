#!/usr/bin/env python3
"""Apply the small Supernote companion bridge to exact E-Ink beta2. GPL-3.0."""
from pathlib import Path
import sys
r=Path(sys.argv[1])
p=r/'build.gradle.kts';s=p.read_text();assert 'extra["bitchordVersionCode"] = 43' in s
s=s.replace('extra["bitchordVersionCode"] = 43','extra["bitchordVersionCode"] = 44').replace('"eink-beta2-poweroff"','"eink-beta3-plugin"');p.write_text(s)
p=r/'app/src/main/AndroidManifest.xml';s=p.read_text();assert '<application' in s
s=s.replace('</application>', '''    <!-- External callers can only show a confirmation; never silently shut down. -->
        <activity android:name=".EInkPluginPowerActivity" android:exported="true"
            android:theme="@android:style/Theme.Material.Light.NoActionBar"
            android:taskAffinity="com.music.bitchord.eink.pluginpower"
            android:excludeFromRecents="true" android:autoRemoveFromRecents="true" />
    </application>''');p.write_text(s)
(r/'app/src/main/java/com/music/bitchord/EInkPluginPowerActivity.kt').write_text('''/* Unofficial BitChord E-Ink extension, GPL-3.0, 2026-11-23. */
package com.music.bitchord

import android.app.Activity
import android.app.AlertDialog
import android.os.Bundle
import android.graphics.Color
import android.widget.TextView
import android.view.Gravity
import android.view.WindowManager

/** A visible, confirmation-only entry point. No service, credentials or arbitrary commands. */
class EInkPluginPowerActivity : Activity() {
    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        window.setBackgroundDrawableResource(android.R.color.white)
        window.addFlags(WindowManager.LayoutParams.FLAG_DIM_BEHIND)
        window.attributes = window.attributes.apply { dimAmount = 0f }
        val message = TextView(this).apply {
            text = "BitChord E-Ink"; textSize = 24f; setTextColor(Color.BLACK)
            setBackgroundColor(Color.WHITE); gravity = Gravity.CENTER
        }
        setContentView(message)
        if (EInkPower.isOff || EInkPower.shuttingDown) { finishAndRemoveTask(); return }
        val dialog = AlertDialog.Builder(this)
            .setTitle("Power off BitChord?")
            .setMessage("Stop music, cancel unfinished downloads and scheduled background work, and close BitChord. Saved music and settings are kept.\\n\\nYour Supernote and its note-taking app stay on.")
            .setNegativeButton("Cancel") { _, _ -> finishAndRemoveTask() }
            .setPositiveButton("Power off", null)
            .setOnCancelListener { finishAndRemoveTask() }
            .create()
        dialog.setOnShowListener {
            dialog.getButton(AlertDialog.BUTTON_POSITIVE).apply {
                filterTouchesWhenObscured = true
                setTextColor(Color.BLACK)
                setOnClickListener {
                    EInkPower.powerOff(this@EInkPluginPowerActivity)
                    if (EInkPower.shuttingDown) {
                        isEnabled = false
                        dialog.getButton(AlertDialog.BUTTON_NEGATIVE).isEnabled = false
                        dialog.setCancelable(false)
                        dialog.setMessage("Stopping BitChord and its background work…")
                    }
                }
            }
            dialog.getButton(AlertDialog.BUTTON_NEGATIVE).setTextColor(Color.BLACK)
        }
        dialog.show()
    }
}
''')
(r/'SUPERNOTE-COMPANION.md').write_text('''# Supernote companion bridge — experimental\n\nAdds a confirmation-only Activity used by BitChord Notes. It delegates to the\nexisting beta2 EInkPower shutdown code. The plugin disconnects its MediaBrowser\nbinding before launching this Activity. It never kills Supernote PluginHost.\n\nPackage remains com.music.bitchord.eink, versionCode 44. The build must retain\nthe beta2 signing certificate; do not uninstall beta2 to install this update.\nPlayback, source integrations and library code are unchanged from beta2.\n\nNo physical Supernote validation is claimed.\n''')
print('Companion patch applied: version, manifest, confirmation Activity; playback engine unchanged')
