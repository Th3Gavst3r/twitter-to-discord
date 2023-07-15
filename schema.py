from typing import Any, Dict

from pydantic import BaseModel as Base


class Tweet(Base):
    """Represents a status update from a twitter user.

    This object is a subclass of the pydantic BaseModel which makes it easy to serialize
    the object with the .dict() and json() methods.

    Attributes:
        tweet_id: Twitter assigned id associated with the tweet.
        tweet_url: Twitter assigned url that links to the tweet.
        is_retweet: Represents if the tweet is a retweet.
        is_pinned: Represents if the user has pinned the tweet.
        time: Time the user sent the tweet.
        text: Text contents of the tweet.
        replies: A count of the replies to the tweet.
        retweets: A count of the times the tweet was retweeted.
        likes: A count of the times the tweet was liked.
        entries: Contains the entries object which holds metadata
            on the tweets text contents.

    """

    tweet_id: int
    tweet_url: str
    username: str
    is_retweet: bool

    @classmethod
    def from_dict(cls, elements: Dict[str, Any]) -> "Tweet":
        """Creates Tweet object from a dictionary of processed text elements.

        Args:
            elements: Preprocessed attributes of a tweet object.

        Returns:
            Tweet object.

        """
        return cls(**elements)
