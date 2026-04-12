# Retrofit
-keep class retrofit2.** { *; }
-keep interface retrofit2.** { *; }
-keepattributes Signature
-keepattributes Exceptions

# GSON
-keep class com.google.gson.** { *; }
-keepattributes EnclosingMethod
-keepattributes InnerClasses

# OkHttp
-keep class okhttp3.** { *; }
-keep interface okhttp3.** { *; }

# Firebase
-keep class com.google.firebase.** { *; }

# Kotlin
-keepnames class kotlin.** { *; }
