#!/usr/bin/env python3
"""
Script to create a Telegraph account and generate an access token.
Run this once to get your Telegraph token for the .env file.
"""

import sys
import os

def create_telegraph_account():
    """Create a Telegraph account and return the access token"""
    try:
        from telegraph import Telegraph
        
        telegraph = Telegraph()
        
        print("Creating Telegraph account...")
        
        response = telegraph.create_account(
            short_name='YouTubeBot',
            author_name='YouTube Summarizer Bot',
            author_url='https://github.com/youtube-summarizer-bot'
        )
        
        print(f"Response: {response}")
        
        # Extract access token from response
        access_token = None
        if response and 'access_token' in response:
            access_token = response['access_token']
        elif response and isinstance(response, dict):
            # Sometimes the token is directly in the response
            for key, value in response.items():
                if 'token' in key.lower() and isinstance(value, str):
                    access_token = value
                    break
        
        if access_token:
            print(f"\n✅ Telegraph account created successfully!")
            print(f"📝 Access Token: {access_token}")
            print(f"\n🔧 Add this to your .env file:")
            print(f"TELEGRAPH_TOKEN={access_token}")
            
            # Optionally write to .env file
            env_path = '.env'
            if os.path.exists(env_path):
                print(f"\n📄 Current .env file exists. Would you like to add the token? (y/n): ", end='')
                choice = input().lower().strip()
                
                if choice == 'y':
                    with open(env_path, 'r') as f:
                        env_content = f.read()
                    
                    # Check if TELEGRAPH_TOKEN already exists
                    if 'TELEGRAPH_TOKEN=' in env_content:
                        print("⚠️  TELEGRAPH_TOKEN already exists in .env file.")
                        print("Please update it manually or remove the existing line.")
                    else:
                        with open(env_path, 'a') as f:
                            f.write(f"\nTELEGRAPH_TOKEN={access_token}\n")
                        print("✅ Token added to .env file!")
            
            return access_token
        else:
            print("❌ Failed to extract access token from response")
            print("Response structure:", response)
            return None
            
    except ImportError:
        print("❌ Telegraph library not installed. Install it with:")
        print("pip install telegraph")
        return None
    except Exception as e:
        print(f"❌ Error creating Telegraph account: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    print("=== Telegraph Account Creator ===\n")
    
    token = create_telegraph_account()
    
    if token:
        print(f"\n🎉 Success! Your Telegraph token is ready to use.")
        print(f"📋 Token: {token}")
        print(f"\n📝 Next steps:")
        print(f"1. Add TELEGRAPH_TOKEN={token} to your .env file")
        print(f"2. Restart your bot to use the new token")
    else:
        print(f"\n❌ Failed to create Telegraph account.")
        print(f"Please check the error messages above and try again.")


if __name__ == "__main__":
    main()
