from pprint import pprint
import requests
from requests.status_codes import codes
import logging
import time

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

            new_tweets = []
            seen_limit = 10
            for tweet in get_tweets(user['username'], pages, address='https://nitter.lacontrevoie.fr'):
                logging.debug(f'Processing tweet {tweet.tweet_id}')

                if ('tweets' not in destination):
                    destination['tweets'] = []

                if ('tweets' not in user):
                    user['tweets'] = []

                if (tweet in destination['tweets']):
                    if (tweet in user['tweets']):
                        if (tweet.is_pinned):
                            logger.info(f'Skipping pin {tweet.tweet_id} because it was already posted')
                            continue
                        else:
                            if (seen_limit == 0):
                                logger.info(f'Reached end of {user["username"]}\'s new tweets')
                                break
                            else:
                                # Guard against self-retweets or users deleting a retweet and retweeting it again later
                                logger.info(f'Skipping tweet {tweet.tweet_id} because it was already posted')
                                seen_limit -= 1
                                continue
                    else:
                        user['tweets'].append(tweet.dict())
                        is_updated = True

                        logger.info(f'Skipping tweet {tweet.tweet_id} because it was already posted by another user')
                        continue

                if ('disable_retweets' in user and user['disable_retweets'] and tweet.is_retweet):
                    logging.info(f'Ignoring {user["username"]}\'s retweet of {tweet.tweet_id}')
                    continue

                seen_limit = 10
                new_tweets.append(tweet)
                destination['tweets'].append(tweet.dict())
                user['tweets'].append(tweet.dict())
                is_updated = True

            # Post in order from oldest to newest
            for tweet in reversed(new_tweets):
                tweet_url = f'https://fxtwitter.com{tweet.tweet_url}'
                body = {
                    'content': tweet_url
                }

                logging.info(f'Posting new tweet: {tweet_url}')

                def post_tweet(tweet_id, retries=5):
                    try:
                        r = requests.post(destination['webhook_url'], body)
                        r.raise_for_status()
                    except requests.exceptions.HTTPError as e:
                        if e.response.status_code == codes.too_many_requests:
                            if (retries > 0) :
                                logging.debug(f'Rate limit exeeded. Retrying after {r.headers["retry-after"]}ms')
                                retry_after = int(r.headers['retry-after']) / 1000
                                time.sleep(retry_after)
                                post_tweet(tweet_id, retries-1)
                            else:
                                logging.error(f'Ran out of retries. Aborting post for tweet {tweet_id}')
                        else:
                            raise e

                post_tweet(tweet.tweet_id)

        if is_updated:
            logging.info(f'Updating document for destination {destination_snapshot.id}')
            db.collection('destinations').document(destination_snapshot.id).set(destination)

    logging.info('Tweets refreshed')
    return 'Tweets refreshed'
