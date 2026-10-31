"""Small text helpers shared by the GUI, speech, and chat modules."""


def AnswerModifier(Answer):
    lines = (Answer or "").split("\n")
    non_empty_lines = [line for line in lines if line.strip()]
    return "\n".join(non_empty_lines)


def QueryModifier(Query):
    new_query = (Query or "").lower().strip()
    if not new_query:
        return ""

    query_words = new_query.split()
    question_words = [
        "how", "what", "who", "where", "when", "why", "which", "whose", "whom",
        "can you", "what's", "where's", "how's",
    ]

    if any(word + " " in new_query for word in question_words):
        if query_words[-1][-1] in [".", "?", "!"]:
            new_query = new_query[:-1] + "?"
        else:
            new_query += "?"
    else:
        if query_words[-1][-1] in [".", "?", "!"]:
            new_query = new_query[:-1] + "."
        else:
            new_query += "."

    return new_query.capitalize()
