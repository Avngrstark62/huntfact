package com.abhijeet.huntfact.hunts

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken

object HuntLocalStore {
    private const val SHARED_PREF_NAME_LEGACY = "hunt_history_store"
    private const val SHARED_PREF_NAME_SECURE = "hunt_history_store_secure"
    private const val HUNTS_KEY = "hunts"
    private val gson = Gson()
    private val securePrefsLock = Any()

    private fun legacyPrefs(context: Context): SharedPreferences {
        return context.getSharedPreferences(SHARED_PREF_NAME_LEGACY, Context.MODE_PRIVATE)
    }

    private fun securePrefsOrNull(context: Context): SharedPreferences? {
        return runCatching {
            val masterKey = MasterKey.Builder(context)
                .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
                .build()
            EncryptedSharedPreferences.create(
                context,
                SHARED_PREF_NAME_SECURE,
                masterKey,
                EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
                EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
            )
        }.getOrNull()
    }

    private fun huntPrefs(context: Context): SharedPreferences {
        val securePrefs = securePrefsOrNull(context)
        if (securePrefs == null) {
            return legacyPrefs(context)
        }
        migrateLegacyHuntsToSecure(context, securePrefs)
        return securePrefs
    }

    private fun migrateLegacyHuntsToSecure(context: Context, securePrefs: SharedPreferences) {
        synchronized(securePrefsLock) {
            val secureData = securePrefs.getString(HUNTS_KEY, null)
            if (!secureData.isNullOrBlank()) {
                return
            }
            val legacyStore = legacyPrefs(context)
            val legacyData = legacyStore.getString(HUNTS_KEY, null)
            if (legacyData.isNullOrBlank()) {
                return
            }
            securePrefs.edit().putString(HUNTS_KEY, legacyData).apply()
            legacyStore.edit().remove(HUNTS_KEY).apply()
        }
    }

    fun saveHunts(context: Context, hunts: List<HuntItem>) {
        val appContext = context.applicationContext
        val serialized = gson.toJson(hunts)
        huntPrefs(appContext)
            .edit()
            .putString(HUNTS_KEY, serialized)
            .apply()
        securePrefsOrNull(appContext)?.let {
            legacyPrefs(appContext).edit().remove(HUNTS_KEY).apply()
        }
    }

    fun readHunts(context: Context): List<HuntItem> {
        val appContext = context.applicationContext
        val raw = huntPrefs(appContext).getString(HUNTS_KEY, null)
            ?: return emptyList()

        val type = object : TypeToken<List<HuntItem>>() {}.type
        return runCatching { gson.fromJson<List<HuntItem>>(raw, type) }.getOrDefault(emptyList())
    }

    fun upsertHunt(context: Context, hunt: HuntItem) {
        val existing = readHunts(context).toMutableList()
        val index = existing.indexOfFirst { it.id == hunt.id }
        if (index >= 0) {
            existing[index] = hunt
        } else {
            existing.add(0, hunt)
        }
        saveHunts(context, existing.sortedByDescending { it.updatedAt ?: it.createdAt ?: "" })
    }
}
