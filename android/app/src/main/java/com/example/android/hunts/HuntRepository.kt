package com.example.android.hunts

import android.content.Context
import com.example.android.network.RetrofitClient

class HuntRepository(private val context: Context) {
    private val apiService = RetrofitClient.getApiService(context = context.applicationContext)

    fun getCachedHunts(): List<HuntItem> = HuntLocalStore.readHunts(context)

    suspend fun syncHunts(): List<HuntItem> {
        val remote = apiService.getHunts().map { it.toHuntItem() }
        HuntLocalStore.saveHunts(context, remote)
        return remote
    }

    suspend fun fetchHunt(huntId: Int): HuntItem {
        val hunt = apiService.getHunt(huntId).toHuntItem()
        HuntLocalStore.upsertHunt(context, hunt)
        return hunt
    }

    fun upsertLocal(hunt: HuntItem) {
        HuntLocalStore.upsertHunt(context, hunt)
    }
}
