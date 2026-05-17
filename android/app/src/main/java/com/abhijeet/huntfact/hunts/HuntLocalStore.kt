package com.abhijeet.huntfact.hunts

import android.content.Context
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken

object HuntLocalStore {
    private const val SHARED_PREF_NAME = "hunt_history_store"
    private const val HUNTS_KEY = "hunts"
    private val gson = Gson()

    fun saveHunts(context: Context, hunts: List<HuntItem>) {
        val serialized = gson.toJson(hunts)
        context.getSharedPreferences(SHARED_PREF_NAME, Context.MODE_PRIVATE)
            .edit()
            .putString(HUNTS_KEY, serialized)
            .apply()
    }

    fun readHunts(context: Context): List<HuntItem> {
        val raw = context.getSharedPreferences(SHARED_PREF_NAME, Context.MODE_PRIVATE)
            .getString(HUNTS_KEY, null)
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
