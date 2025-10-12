"""
Test Telegram Alert Functionality
==================================

This script tests if Telegram alerts are working correctly.
"""

import sys
import io

# Fix Windows encoding issues
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import requests

# Telegram credentials
bot_token = "8333626494:AAElu5g-jy0ilYkg5-pqpujIH-jWVsdXeLs"
receiver_chat_id = "509536698"

def test_telegram_message():
    """Test sending a Telegram message"""

    print("="*80)
    print("TESTING TELEGRAM ALERT FUNCTIONALITY")
    print("="*80)

    # Test message
    test_message = """🤖 Paper Trading Alert Test

This is a test message from your trading bot!

Status: ✅ Telegram integration working
Time: Testing phase
Bot: Single Trade Focus Bot

If you receive this message, your Telegram alerts are configured correctly! 🎉"""

    try:
        print(f"\nSending test message to chat ID: {receiver_chat_id}")

        # Send message via Telegram API
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            'chat_id': receiver_chat_id,
            'text': test_message
        }

        response = requests.post(url, json=payload, timeout=10)

        if response.status_code == 200:
            print("✅ SUCCESS! Telegram message sent successfully!")
            print(f"\nResponse: {response.json()}")
            print("\n✅ Check your Telegram app - you should see the test message!")
            return True
        else:
            print(f"FAILED! Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_telegram_message()
    print("\n" + "="*80)