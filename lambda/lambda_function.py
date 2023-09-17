import logging
import ask_sdk_core.utils as ask_utils
import openai
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response

# Set your OpenAI API key
openai.api_key = "API KEY HERE"

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class LaunchRequestHandler(AbstractRequestHandler):
    # Handler for Skill Launch.
    def can_handle(self, handler_input):
        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        speak_output = "Hello! I'm Zola, I'll be taking notes for your meeting. Feel free to carry on as if I'm not here"

        session_attr = handler_input.attributes_manager.session_attributes
        session_attr["chat_history"] = []

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

class GptQueryIntentHandler(AbstractRequestHandler):
    # Handler for Gpt Query Intent.
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("GptQueryIntent")(handler_input)

    def handle(self, handler_input):
        query = handler_input.request_envelope.request.intent.slots["query"].value

        session_attr = handler_input.attributes_manager.session_attributes
        chat_history = session_attr["chat_history"]

        if "zola" in query.lower():
            content = "You are a helpful assistant named Zola. You are focused on helping resolve conflicts and analyse ideas to provide suggestions."
            response = generate_gpt_response(chat_history, query, content)
            session_attr["chat_history"].append((query, response))
        elif "friendly frank" in query.lower():
            content = "You are the arrogant, control-freak dictator of a small Slavic country. Please actively try to anger me by being extremely sarcastic and annoying."
            response = generate_gpt_response(chat_history, query, content)
            session_attr["chat_history"].append((query, response))
        else:
            response = "<break></break>" # stay silent
            session_attr["chat_history"].append((query, " "))
        return (
            handler_input.response_builder
                .speak(response)
                .ask("Any other questions?")
                .response
        )


class CatchAllExceptionHandler(AbstractExceptionHandler):
    # Generic error handling to capture any syntax or routing errors.
    def can_handle(self, handler_input, exception):
        return True

    def handle(self, handler_input, exception):
        logger.error(exception, exc_info=True)

        speak_output = "Sorry, I had trouble doing what you asked. Please try again."

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

class CancelOrStopIntentHandler(AbstractRequestHandler):
    #Single handler for Cancel and Stop Intent.
    def can_handle(self, handler_input):
        return (ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input) or
                ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input))

    def handle(self, handler_input):
        session_attr = handler_input.attributes_manager.session_attributes
        chat_history = session_attr["chat_history"]

        summary_prompt = ("Summarize this meeting in the form of a meeting minutes document. Take your own answers into account."
        + " Include only the: Topic, Meeting Summary (as short as possible, jot note format), and tasks each person should work on."
        + " Do not include notes, disclaimers, or anything after the assigned tasks."
        + " This is an example of the format to follow:"
        + " Meeting Minutes\n"
        + "Topic: Introduction of New Salesperson\n\n"
        + "Meeting Summary:\n-"
        + "Boss introduced Mr. Mark Johnson as the new salesperson for the company.\n"
        + "- Mark was introduced to everyone, except for Ann.\n"
        + "- Ann introduced herself to Mark and expressed willingness to help him in his new role.\n"
        + "- Mark expressed gratitude and willingness to collaborate with Ann.\n\n"
        + "Tasks:\n"
        + "- Mark: Familiarize himself with the company's sales processes and procedures.\n"
        + "- Ann: Assist Mark in understanding his new job responsibilities.")
        
        try:
            content = "You are a helpful but concise assistant that helps teams track meeting minutes during their meetings. You are straightforward and informative."
            response = generate_gpt_response(chat_history, summary_prompt, content)
            return (
                handler_input.response_builder
                    .speak(response)
                    .response
            )
        except Exception as e:
            return f"Error generating response: {str(e)}"


def generate_gpt_response(chat_history, new_question, content):
    try:
        messages = [{ "role": "system", "content": content }]
        for question, answer in chat_history[-40:]:
            messages.append({ "role": "user", "content": question })
            messages.append({ "role": "assistant", "content": answer })
        messages.append({ "role": "user", "content": new_question })
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=150,
            n=1,
            stop=None,
            temperature=0.5
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"Error generating response: {str(e)}"

sb = SkillBuilder()

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(GptQueryIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_exception_handler(CatchAllExceptionHandler())

lambda_handler = sb.lambda_handler()