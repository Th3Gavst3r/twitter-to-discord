from pprint import pprint
import requests

from cloudevents.http import CloudEvent
import functions_framework
import firebase_admin
from firebase_admin import firestore

from nitter_scraper import get_tweets


# Application Default credentials are automatically created.
app = firebase_admin.initialize_app()
db = firestore.client()

def twitter_to_discord(data, context=None) -> str:
    destinations = db.collection('destinations').stream()

    for destination_snapshot in destinations:
        destination = destination_snapshot.to_dict()
        is_updated = False

        if ('users' not in destination):
            destination['users'] = []
            is_updated = True

        for user in destination['users']:
            for tweet in get_tweets(user['username'], pages=5):
                if ('disable_retweets' in user and user['disable_retweets'] and tweet.is_retweet):
                    continue

                if ('tweets' not in destination):
                    destination['tweets'] = []

                if (tweet not in destination['tweets']):
                    tweet_url = f'https://twitter.com{tweet.tweet_url}'
                    body = {
                        'content': tweet_url
                    }

                    print(f'Posting new tweet: {tweet_url}')
                    requests.post(destination['webhook_url'], body)

                    destination['tweets'].append(tweet.dict())
                    is_updated = True

        if is_updated:
            db.collection('destinations').document(destination_snapshot.id).set(destination)

    print('Tweets refreshed')
    return 'Tweets refreshed'
