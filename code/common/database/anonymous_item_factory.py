import re

from .anonymous_item import AnonymousItem
from .detailed_item import DetailedItem

class AnonymousItemFactory:
    ## Mentioned users with channel permissions will be of the form <@\d+>, while mentioned users without permissions
    ## will be of the form <@&\d+>.
    MENTION_REGEX = re.compile("<@(&?\d+)>")
    ANONYMOUS_USER_PREFIX = "user"


    @staticmethod
    def create(detailed_item: DetailedItem) -> AnonymousItem:
        context = detailed_item.discord_context
        command = detailed_item.command
        query_text = AnonymousItemFactory._anonymize_query_text(detailed_item.query)
        is_valid = detailed_item.is_valid

        return AnonymousItem(context, command, query_text, is_valid)


    @staticmethod
    def _anonymize_query_text(query_text: str) -> str:
        matches = AnonymousItemFactory.MENTION_REGEX.finditer(query_text)

        counter = 0
        user_id_to_anonymous_user_id_map = {}

        ## Accumulate all mentions and build anonymized versions for each unique one
        for match in matches:
            user_id = match.group(1)

            if (user_id not in user_id_to_anonymous_user_id_map):
                anonymous_user_id = f"{AnonymousItemFactory.ANONYMOUS_USER_PREFIX}{counter}"

                user_id_to_anonymous_user_id_map[user_id] = anonymous_user_id
                counter += 1
            else:
                anonymous_user_id = user_id_to_anonymous_user_id_map[user_id]

        output = query_text
        for user_id, anonymous_user_id in user_id_to_anonymous_user_id_map.items():
            output = output.replace(user_id, anonymous_user_id)

        return output;
