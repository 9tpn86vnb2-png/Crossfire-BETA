/* Unofficial BitChord E-Ink modification, GPL-3.0, 2026-11-23. */
package com.music.bitchord.ui.components

import android.app.Activity
import android.content.Context
import android.content.ContextWrapper
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.PowerSettingsNew
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.music.bitchord.EInkPower

private fun Context.hostActivity(): Activity? = when (this) {
    is Activity -> this
    is ContextWrapper -> baseContext.hostActivity()
    else -> null
}

@Composable
fun EInkPowerButton(showLabel: Boolean = false) {
    val activity = LocalContext.current.hostActivity()
    var confirm by remember { mutableStateOf(false) }
    var closing by remember { mutableStateOf(false) }
    if (showLabel) {
        OutlinedButton(onClick = { confirm = true }, enabled = !closing && activity != null,
            modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 8.dp).heightIn(min = 52.dp)) {
            Icon(Icons.Rounded.PowerSettingsNew, contentDescription = null)
            Spacer(Modifier.width(12.dp))
            Text("Power off BitChord")
        }
    } else {
        IconButton(onClick = { confirm = true }, enabled = !closing && activity != null) {
            Icon(Icons.Rounded.PowerSettingsNew, contentDescription = "Power off BitChord")
        }
    }
    if (confirm) {
        AlertDialog(
            onDismissRequest = { if (!closing) confirm = false },
            title = { Text(if (closing) "Closing BitChord…" else "Power off BitChord?") },
            text = { Text(if (closing) "Stopping audio and background work…" else
                "Stop music, cancel unfinished downloads, leave listening sessions, and close BitChord's background process. Scheduled sync and backups stay paused until you reopen BitChord.\n\nSaved music, playlists, and settings are kept. This does not turn off your Supernote.") },
            confirmButton = { TextButton(enabled = !closing, onClick = {
                activity?.let { EInkPower.powerOff(it); closing = EInkPower.shuttingDown }
            }) { Text("Power off") } },
            dismissButton = { if (!closing) TextButton(onClick = { confirm = false }) { Text("Cancel") } },
        )
    }
}
