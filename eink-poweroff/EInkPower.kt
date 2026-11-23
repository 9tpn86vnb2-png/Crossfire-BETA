/* Unofficial BitChord E-Ink modification, GPL-3.0, 2026-11-23. */
package com.music.bitchord

import android.app.Activity
import android.app.ActivityManager
import android.app.NotificationManager
import android.app.job.JobScheduler
import android.content.Context
import android.content.Intent
import android.os.Handler
import android.os.Looper
import android.os.Process
import android.widget.Toast
import androidx.work.WorkManager
import com.music.bitchord.download.Downloads
import com.music.bitchord.download.DownloadService
import com.music.bitchord.playback.PlaybackService
import com.music.bitchord.data.listentogether.ListenTogether
import kotlinx.coroutines.*
import java.util.concurrent.TimeUnit

/** Explicit app shutdown, not Android's privileged package force-stop or tablet power-off. */
object EInkPower {
    private const val PREFS = "eink_power"
    @Volatile var isOff: Boolean = false
        private set
    @Volatile var shuttingDown: Boolean = false
        private set
    // Set/cleared by the service on the main thread. No activity reference is retained.
    internal var stopPlayback: (() -> Unit)? = null
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)

    fun load(context: Context) {
        isOff = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getBoolean("off", false)
        if (isOff) {
            // Android may briefly start a process for an old broadcast/binding.
            // Do not leave that process resident after the user's explicit exit.
            Handler(Looper.getMainLooper()).postDelayed({
                if (isOff && !shuttingDown) Process.killProcess(Process.myPid())
            }, 1800L)
        }
    }

    fun open(activity: Activity): Boolean {
        if (shuttingDown) return false
        if (isOff) {
            if (!activity.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                    .edit().putBoolean("off", false).commit()) {
                Toast.makeText(activity, "Could not save power state. Check free storage.", Toast.LENGTH_LONG).show()
                return false
            }
            isOff = false
            (activity.application as BitChordApplication).startActiveFeatures()
        }
        return true
    }

    fun powerOff(activity: Activity) {
        if (shuttingDown) return
        // Commit the intent before terminating anything. Failure leaves the app usable.
        if (!activity.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                .edit().putBoolean("off", true).commit()) {
            Toast.makeText(activity, "Could not save power state. Nothing was closed.", Toast.LENGTH_LONG).show()
            return
        }
        isOff = true
        shuttingDown = true
        // This hook pauses BOTH crossfade players and saves a bounded queue snapshot
        // synchronously before stop(), which might otherwise lose its position.
        runCatching { stopPlayback?.invoke() }
        Downloads.active.value.keys.toList().forEach { runCatching { Downloads.cancel(it) } }
        runCatching { activity.stopService(Intent(activity, DownloadService::class.java)) }

        val app = activity.applicationContext
        scope.launch {
            // Cancel persisted WorkManager requests and wait for the database transaction.
            // Merely killing a sticky service/process causes Android to restart it.
            val cancelled = withContext(Dispatchers.IO) {
                runCatching {
                    WorkManager.getInstance(app).cancelAllWork().result.get(12, TimeUnit.SECONDS)
                }.isSuccess
            }
            if (!cancelled) {
                // Jobs are also cancelled below; the persistent off latch makes a stale
                // worker a no-op. Do not misrepresent this as a system force-stop.
                Toast.makeText(app, "Closing BitChord. Background jobs are blocked until you reopen it.", Toast.LENGTH_LONG).show()
            }
            withTimeoutOrNull(1500L) { runCatching { ListenTogether.leaveParty() } }
            runCatching { app.getSystemService(JobScheduler::class.java)?.cancelAll() }
            // All declared services belong to this package, including WorkManager's
            // foreground service and the watch helper. No other app is targeted.
            @Suppress("DEPRECATION")
            val services = app.packageManager.getPackageInfo(app.packageName,
                android.content.pm.PackageManager.GET_SERVICES).services.orEmpty()
            services.forEach { service ->
                runCatching { app.stopService(Intent().setClassName(app.packageName, service.name)) }
            }
            runCatching { app.getSystemService(NotificationManager::class.java)?.cancelAll() }
            // Remove every task owned by this app. Disposing Compose also releases
            // the MediaController binding, allowing normal service onDestroy cleanup.
            runCatching { activity.getSystemService(ActivityManager::class.java)?.appTasks
                ?.forEach { it.finishAndRemoveTask() } }
            activity.finishAndRemoveTask()
            // Give cancellation finalizers and the normal service teardown time to run.
            delay(1200L)
            withContext(Dispatchers.IO) {
                // A commit barrier drains earlier SharedPreferences.apply writes in
                // each store without changing their values or erasing user data.
                val dir = java.io.File(app.applicationInfo.dataDir, "shared_prefs")
                dir.listFiles()?.filter { it.extension == "xml" }?.forEach { file ->
                    runCatching { app.getSharedPreferences(file.nameWithoutExtension,
                        Context.MODE_PRIVATE).edit().commit() }
                }
            }
            runCatching { app.getSystemService(JobScheduler::class.java)?.cancelAll() }
            runCatching { app.getSystemService(NotificationManager::class.java)?.cancelAll() }
            Process.killProcess(Process.myPid())
        }
    }
}
