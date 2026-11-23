#!/usr/bin/env python3
"""Apply power-off changes to the exact BitChord E-Ink beta1 source. GPL-3.0."""
from pathlib import Path
import sys, json
root = Path(sys.argv[1]); here = Path(__file__).parent
A = 'app/src/main/java/com/music/bitchord/'
changed = []
def edit(path, before, after, count=1):
    p=root/path; s=p.read_text()
    assert s.count(before)==count, (path, before[:100], s.count(before), count)
    p.write_text(s.replace(before, after)); changed.append(path)

def guard(path, signature, condition='com.music.bitchord.EInkPower.isOff', result='return'):
    edit(A+path, signature, signature+'\n        if ('+condition+') '+result)

for name in ['EInkPower.kt', 'EInkPowerButton.kt']:
    dst=A+(name if name=='EInkPower.kt' else 'ui/components/'+name)
    (root/dst).write_text((here/name).read_text()); changed.append(dst)
edit('build.gradle.kts','extra["bitchordVersionCode"] = 42','extra["bitchordVersionCode"] = 43')
edit('build.gradle.kts','extra["bitchordBetaSuffix"] = "eink-beta1"','extra["bitchordBetaSuffix"] = "eink-beta2-poweroff"')
edit(A+'BitChordApplication.kt','        super.onCreate()','        super.onCreate()\n        EInkPower.load(this)')
features=['com.music.bitchord.playback.smart.AutomixModels.install(this)',
          'ListenTogether.init(this)', 'PlaylistSync.init(this)',
          'com.music.bitchord.data.backup.DriveBackup.init(this)',
          'com.music.bitchord.data.presence.AndroidPresence.install(this)']
for f in features:
    edit(A+'BitChordApplication.kt', '        '+f, '        // Deferred to startActiveFeatures(): '+f)
edit(A+'BitChordApplication.kt','        backgroundInit.join()\n    }',
     '        backgroundInit.join()\n        startActiveFeatures()\n    }\n\n'
     '    private var activeFeaturesStarted = false\n'
     '    internal fun startActiveFeatures() {\n'
     '        if (activeFeaturesStarted || EInkPower.isOff) return\n'
     '        activeFeaturesStarted = true\n'+''.join('        '+f+'\n' for f in features)+'    }')
edit(A+'BitChordApplication.kt','            CoroutineScope(Dispatchers.IO).launch { Innertube.ensureSessionScope() }',
     '            if (!EInkPower.isOff) CoroutineScope(Dispatchers.IO).launch { Innertube.ensureSessionScope() }')
edit(A+'MainActivity.kt','        super.onCreate(savedInstanceState)\n        enableEdgeToEdge()',
     '        super.onCreate(savedInstanceState)\n'
     '        if (!EInkPower.open(this)) { finish(); return }\n        enableEdgeToEdge()')
edit(A+'MainActivity.kt','                    actions = {\n                        // This is intentionally scoped',
     '                    actions = {\n                        com.music.bitchord.ui.components.EInkPowerButton()\n                        // This is intentionally scoped')
edit(A+'ui/screens/SettingsSheet.kt','        SettingsPageTitle(stringResource(section?.title ?: R.string.settings))',
     '        SettingsPageTitle(stringResource(section?.title ?: R.string.settings))\n'
     '        if (section == null) com.music.bitchord.ui.components.EInkPowerButton(showLabel = true)')
p=A+'playback/PlaybackService.kt'
edit(p,'    override fun onCreate() {\n        super.onCreate()',
     '''    private var rejectedPowerOffStart = false

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (com.music.bitchord.EInkPower.isOff) {
            stopSelf()
            return START_NOT_STICKY
        }
        return super.onStartCommand(intent, flags, startId)
    }

    override fun onCreate() {
        super.onCreate()
        if (com.music.bitchord.EInkPower.isOff) {
            rejectedPowerOffStart = true
            stopSelf()
            return
        }
        com.music.bitchord.EInkPower.stopPlayback = {
            crossfade?.cancelAutoMixVisual()
            if (castPlayback.active) CastController.disconnect(resumeHere = false)
            eachPlayer { it.pause() }
            player?.let { saveQueueSnapshotImmediately(it) }
            eachPlayer { it.stop() }
            stopForeground(STOP_FOREGROUND_REMOVE)
            stopSelf()
        }''')
edit(p,'        mediaSession\n\n    /**\n     * Called by Android when the user swipes',
     '        if (com.music.bitchord.EInkPower.isOff) null else mediaSession\n\n    /**\n     * Called by Android when the user swipes')
edit(p,'    override fun onDestroy() {\n        crossfade?.cancelAutoMixVisual()',
     '    override fun onDestroy() {\n'
     '        if (rejectedPowerOffStart) { super.onDestroy(); return }\n'
     '        com.music.bitchord.EInkPower.stopPlayback = null\n'
     '        crossfade?.cancelAutoMixVisual()')
guard('download/Downloads.kt', '    fun enqueue(context: Context, song: Song, from: String? = null) {')
guard('download/DownloadService.kt','    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {',
      result='{ stopSelf(); return START_NOT_STICKY }')
for sig in [
 '    fun checkNow(context: Context, approved: Boolean = false) {',
 '    private fun checkLikedSoon(context: Context) {',
 '    private fun schedule(context: Context, wifiOnly: Boolean, replace: Boolean) {']:
    guard('download/PlaylistSync.kt',sig)
guard('download/PlaylistSync.kt','    override suspend fun doWork(): Result {',result='return Result.success()')
guard('data/backup/DriveBackup.kt','    override suspend fun doWork(): Result {',result='return Result.success()')
guard('data/backup/DriveBackup.kt','    private fun schedule(context: Context, frequency: BackupFrequency, cellular: Boolean, replace: Boolean) {')
guard('data/backup/DriveBackup.kt','            override fun onStart(owner: LifecycleOwner) {')
guard('data/backup/DriveBackup.kt','    fun syncNow(context: Context) {')
guard('widget/MediaWidgetActions.kt','    override fun onReceive(context: Context, intent: Intent) {')
guard('widget/PlaybackTile.kt','    override fun onClick() {')
m=root/'EINK-MANIFEST.json'; d=json.loads(m.read_text()); d.update(edition='eink-beta2-poweroff',date='2026-11-23')
d['poweroff_changed']=sorted(set(changed));d['hardware_tested']=False
m.write_text(json.dumps(d,indent=2)+'\n')
(root/'POWER-OFF-CHANGES.md').write_text('''# BitChord E-Ink beta2 — power off
Unofficial GPL-3.0 modification, 2026-11-23.

Power icon in the top bar and a labelled button near the top of Settings.
Confirmation stops both audio players, cancels active/queued downloads, leaves
Listen Together, cancels WorkManager and JobScheduler requests, stops this app's
services, removes its tasks and notifications, drains preference writes and
terminates its own process. Saved completed downloads and library are not erased.
Reopening the app clears the off latch and restores normal scheduled behavior.
Old media-service starts and jobs are blocked while off. Android can briefly
create a process for an external request; this is not a privileged system Force stop.
No tablet power-off, root access, accessibility service or new permissions.
Closing normally/back navigation does not invoke power off.

Source-level changes are listed in EINK-MANIFEST.json. Confirmed test results
must come from the build/test artifacts, not this description. Physical Supernote
hardware, Bluetooth audio, account integration and battery runtime are not tested.
''')
print(json.dumps({'changed':sorted(set(changed))},indent=2))
