package com.abhijeet.huntfact.hunts

import android.content.Context
import com.abhijeet.huntfact.network.RetrofitClient
import com.google.firebase.Firebase
import com.google.firebase.crashlytics.crashlytics

class HuntRepository(private val context: Context) {
    private val apiService = RetrofitClient.getApiService(context = context.applicationContext)

    fun getCachedHunts(): List<HuntItem> {
        Firebase.crashlytics.log("HuntRepository.getCachedHunts: reading local cache")
        val cached = HuntLocalStore.readHunts(context)
        Firebase.crashlytics.log("HuntRepository.getCachedHunts: cacheCount=${cached.size}")
        return cached
    }

    suspend fun syncHunts(): List<HuntItem> {
        Firebase.crashlytics.log("HuntRepository.syncHunts: started")
        Firebase.crashlytics.log("HuntRepository.syncHunts: requesting GET /hunts")
        val remote = apiService.getHunts().map { it.toHuntItem() }
        Firebase.crashlytics.log("HuntRepository.syncHunts: received huntCount=${remote.size}")
        Firebase.crashlytics.log("HuntRepository.syncHunts: saving hunts to local store")
        HuntLocalStore.saveHunts(context, remote)
        Firebase.crashlytics.log("HuntRepository.syncHunts: completed")
        return remote
    }

    suspend fun fetchHunt(huntId: Int): HuntItem {
        Firebase.crashlytics.log("HuntRepository.fetchHunt: started for huntId=$huntId")
        Firebase.crashlytics.log("HuntRepository.fetchHunt: requesting GET /hunts/$huntId")
        val hunt = apiService.getHunt(huntId).toHuntItem()
        Firebase.crashlytics.log("HuntRepository.fetchHunt: persisting huntId=$huntId locally")
        HuntLocalStore.upsertHunt(context, hunt)
        Firebase.crashlytics.log("HuntRepository.fetchHunt: completed for huntId=$huntId")
        return hunt
    }

    fun upsertLocal(hunt: HuntItem) {
        Firebase.crashlytics.log("HuntRepository.upsertLocal: upserting huntId=${hunt.id}")
        HuntLocalStore.upsertHunt(context, hunt)
        Firebase.crashlytics.log("HuntRepository.upsertLocal: completed for huntId=${hunt.id}")
    }
}
