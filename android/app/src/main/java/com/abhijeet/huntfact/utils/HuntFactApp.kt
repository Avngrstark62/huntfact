package com.abhijeet.huntfact.utils

import android.app.Application
import android.content.Context

class HuntFactApp : Application() {
    override fun onCreate() {
        super.onCreate()
        appContext = applicationContext
    }

    companion object {
        private lateinit var appContext: Context

        fun getAppContextOrNull(): Context? {
            return if (::appContext.isInitialized) appContext else null
        }
    }
}
