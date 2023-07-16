from pprint import pprint
import requests
import logging

from cloudevents.http import CloudEvent
import functions_framework
import firebase_admin
from firebase_admin import firestore

from nitter_scraper import get_tweets

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Application Default credentials are automatically created.
app = firebase_admin.initialize_app()
db = firestore.client()

def twitter_to_discord(data, context=None) -> str:
    logging.debug('Received invocation')
    destinations = db.collection('destinations').stream()

    for destination_snapshot in destinations:
        logging.debug(f'Processing destination {destination_snapshot.id}')

        destination = destination_snapshot.to_dict()
        is_updated = False

        if ('users' not in destination):
            destination['users'] = []
            is_updated = True

        for user in destination['users']:
            logging.debug(f'Processing user {user["username"]}')

            pages = 5
            if ('is_new' not in user or user['is_new']):
                logging.debug(f'User {user["username"]} is new. Performing short lookup')
                pages = 1
                user['is_new'] = False
                is_updated = True

            for tweet in get_tweets(user['username'], pages, address='https://nitter.lacontrevoie.fr'):
                logging.debug(f'Processing tweet {tweet.tweet_id}')

                if ('disable_retweets' in user and user['disable_retweets'] and tweet.is_retweet):
                    logging.info(f'Ignoring {user["username"]}\'s retweet of {tweet.tweet_id}')
                    continue

                if ('tweets' not in destination):
                    destination['tweets'] = []

                if (tweet not in destination['tweets']):
                    tweet_url = f'https://twitter.com{tweet.tweet_url}'
                    body = {
                        'content': tweet_url
                    }

                    logging.info(f'Posting new tweet: {tweet_url}')
                    requests.post(destination['webhook_url'], body)

                    destination['tweets'].append(tweet.dict())
                    is_updated = True

        if is_updated:
            logging.info(f'Updating document for destination {destination_snapshot.id}')
            db.collection('destinations').document(destination_snapshot.id).set(destination)

    logging.info('Tweets refreshed')
    return 'Tweets refreshed'
