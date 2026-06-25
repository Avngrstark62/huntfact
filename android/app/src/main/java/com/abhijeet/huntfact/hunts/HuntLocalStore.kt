package com.abhijeet.huntfact.hunts

import android.content.Context
import com.google.firebase.Firebase
import com.google.firebase.crashlytics.crashlytics
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken

object HuntLocalStore {
    private const val SHARED_PREF_NAME = "hunt_history_store"
    private const val HUNTS_KEY = "hunts"
    private val gson = Gson()

    fun saveHunts(context: Context, hunts: List<HuntItem>) {
        Firebase.crashlytics.log("HuntLocalStore.saveHunts: serializing huntCount=${hunts.size}")
        val serialized = gson.toJson(hunts)
        Firebase.crashlytics.log("HuntLocalStore.saveHunts: writing serialized hunts to SharedPreferences")
        context.getSharedPreferences(SHARED_PREF_NAME, Context.MODE_PRIVATE)
            .edit()
            .putString(HUNTS_KEY, serialized)
            .apply()
        Firebase.crashlytics.log("HuntLocalStore.saveHunts: completed")
    }

    fun readHunts(context: Context): List<HuntItem> {
        Firebase.crashlytics.log("HuntLocalStore.readHunts: reading from SharedPreferences")
        val raw = context.getSharedPreferences(SHARED_PREF_NAME, Context.MODE_PRIVATE)
            .getString(HUNTS_KEY, null)
            ?: run {
                Firebase.crashlytics.log("HuntLocalStore.readHunts: no cached hunts found")
                return emptyList()
            }

        val type = object : TypeToken<List<HuntItem>>() {}.type
        return runCatching {
            Firebase.crashlytics.log("HuntLocalStore.readHunts: parsing serialized hunts")
            gson.fromJson<List<HuntItem>>(raw, type)
        }.onFailure { exception ->
            Firebase.crashlytics.log("HuntLocalStore.readHunts: parse failed, returning empty list")
            Firebase.crashlytics.recordException(exception)
        }.getOrDefault(emptyList()).also {
            Firebase.crashlytics.log("HuntLocalStore.readHunts: parsed huntCount=${it.size}")
        }
    }

    fun upsertHunt(context: Context, hunt: HuntItem) {
        Firebase.crashlytics.log("HuntLocalStore.upsertHunt: started for huntId=${hunt.id}")
        val existing = readHunts(context).toMutableList()
        val index = existing.indexOfFirst { it.id == hunt.id }
        if (index >= 0) {
            existing[index] = hunt
        } else {
            existing.add(0, hunt)
        }
        Firebase.crashlytics.log("HuntLocalStore.upsertHunt: saving updated hunt list count=${existing.size}")
        saveHunts(context, existing.sortedByDescending { it.updatedAt ?: it.createdAt ?: "" })
        Firebase.crashlytics.log("HuntLocalStore.upsertHunt: completed for huntId=${hunt.id}")
    }
}
