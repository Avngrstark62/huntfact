from services.reel_extractor import get_reel_video_url
import requests
import asyncio

async def main():
    url = "https://www.instagram.com/reel/DWBrc8Ij6si" # asharam
    # url = "https://www.instagram.com/reel/DYXCY4nMcnq" # qutub minar
    cdn_link = ""
    # cdn_link = "https://scontent.cdninstagram.com/o1/v/t16/f2/m69/AQPK4kM4c772XfeKxBs7787uzgA8d7YYb2v1nnM0ahGnc5xt4aiorcRfGbIbqr1R-QNv95vER7YTFZSdwthwhlg0.mp4?strext=1&_nc_cat=104&_nc_oc=Adp4rDlq1roCeBORCExV5bujzvv12TkKA0LdRDvPovNDAVfqcOfKb1QJLXJF2SRYK774pMoV9LEvzfNi5b7h_Ipn&_nc_sid=5e9851&_nc_ht=instagram.fjlr3-1.fna.fbcdn.net&_nc_ohc=BJYsoXoDolQQ7kNvwHkXeBd&efg=eyJ2ZW5jb2RlX3RhZyI6Inhwdl9wcm9ncmVzc2l2ZS5JTlNUQUdSQU0uQ0xJUFMuQzMuNzIwLmRhc2hfYmFzZWxpbmVfMV92MSIsInhwdl9hc3NldF9pZCI6MTc5NDAxOTg4MTAxNzc0MTMsImFzc2V0X2FnZV9kYXlzIjo1NywidmlfdXNlY2FzZV9pZCI6MTAwOTksImR1cmF0aW9uX3MiOjkxLCJ1cmxnZW5fc291cmNlIjoid3d3In0%3D&ccb=17-1&vs=8986431844e5f206&_nc_vs=HBksFQIYOnBhc3N0aHJvdWdoX2V2ZXJzdG9yZS9HRE4wNGlZNVN3TDRvWHNEQU5KTVpEbklXbUVQYnNwVEFRQUYVAALIARIAFQIYUWlnX3hwdl9wbGFjZW1lbnRfcGVybWFuZW50X3YyLzlBNDE3MTE4MTkyMzM0NzMwMTM3NDRFRTlENzYyQ0FBX2F1ZGlvX2Rhc2hpbml0Lm1wNBUCAsgBEgAoABgAGwKIB3VzZV9vaWwBMRJwcm9ncmVzc2l2ZV9yZWNpcGUBMRUAACaKvr6UgaHePxUCKAJDMywXQFbqn752yLQYEmRhc2hfYmFzZWxpbmVfMV92MREAdf4HZeadAQA&_nc_gid=RQRwIZEh2Hw1vEs7f4yJPw&_nc_zt=28&_nc_ss=7a22e&oh=00_Af6vNtYms9ZUTrettQF7YHr3pVcJsDq0mepI0wX78ovbEA&oe=6A0C6558"
    if not cdn_link:
        cdn_link = get_reel_video_url(url)
    print(f"CDN Link: {cdn_link}")
    fcm_token = "android-simulator-token"
    print("cdn_link:", cdn_link)

    # call the start-hunt api with required request fields
    api_url = "http://localhost:8000/start-hunt"
    # api_url = "https://api.huntfact.com/start-hunt"
    payload = {
        "video_link": url,
        "cdn_link": cdn_link,
        "fcm_token": fcm_token,
    }
    response = requests.post(api_url, json=payload)
    print("API response:", response.json())
if __name__ == "__main__":
    asyncio.run(main())
