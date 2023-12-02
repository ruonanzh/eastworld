import asyncio
import json
import os
import re
from typing import Any, List, Optional, Union, Dict

from openai import AsyncOpenAI
import httpx
#from aiohttp import ClientSession

from llm.base import LLMBase
from schema import ActionCompletion, Message
from abc import ABCMeta

class Singleton(ABCMeta):
    __instances: Dict[Any, Any] = {}
    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        if cls not in cls.__instances:
            cls.__instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls.__instances[cls]

    @classmethod
    def delete_all_instances(cls) -> None:
        cls.__instances = {}
        print("Deleted")

class OpenAIInterface(LLMBase, metaclass=Singleton):
    def __init__(
        self,
        user_api_key: Optional[str] = "",
        model: str = "gpt-4",
        embedding_size: int = 1536,
        api_base: Optional[str] = None,
        client_session: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self._model = model
        self._embedding_size = embedding_size

        if user_api_key == "":
            user_api_key = os.getenv("OPENAI_API_KEY")

        self._client = AsyncOpenAI(api_key = user_api_key, 
                                   http_client = client_session,
                                   timeout=30)

        if api_base is not None:
            self._client.base_url = api_base

        # TODO: does this actually make it faster?
        # openai.aiosession.set(client_session)

    async def completion(
        self,
        messages: List[Message],
        functions: List[Any],
    ) -> Union[Message, ActionCompletion]:
        #chat_function_arguments = _generate_completions_function_args(functions)      

        if(functions.__len__() == 0):
            completion:Any = (
                await self._client.chat.completions.create( # type: ignore
                    model=self._model,
                    messages=_parse_messages_arry(messages),
                )
            ).choices[0].message

            return Message(role="assistant", content=completion.content)
        
        else:
            completion:Any = (
                await self._client.chat.completions.create( # type: ignore
                    model=self._model,
                    messages=_parse_messages_arry(messages),
                    tools=functions,
                )
            ).choices[0].message

            if completion.tool_calls:
                func_call = completion.tool_calls
                # TODO: Sometimes the arguments are malformed.
                try:
                    args = json.loads(func_call.function.arguments)
                except json.JSONDecodeError:
                    args: Any = {}

                return ActionCompletion(action=func_call.function.name, args=args)
            
            return Message(role="assistant", content=completion.content)

    async def chat_completion(
        self,
        messages: List[Message],
    ) -> Message:
        completion: Any = (
            await self._client.chat.completions.create(  # type: ignore
                messages=_parse_messages_arry(messages),
                model=self._model,
            )
        ).choices[0].message

        return Message(role="assistant", content=completion.content)

    async def action_completion(
        self,
        messages: List[Message],
        functions: List[Any],
    ) -> Optional[ActionCompletion]:
        retries = 3

        for _ in range(retries):
            completion: Any = (
                await self._client.chat.completions.create(  # type: ignore
                    model=self._model,
                    messages=_parse_messages_arry(messages),
                    #change in openai 1.0.0 need to make it better
                    #**chat_function_arguments,
                    tools=functions,
                    tool_choice="auto",
                )
            ).choices[0].message

            if completion.tool_calls:
                func_call = completion.tool_calls
                # TODO: Sometimes the arguments are malformed.
                try:
                    args = json.loads(func_call.function.arguments)
                except json.JSONDecodeError:
                    args: Any = {}

                return ActionCompletion(action=func_call.function.name, args=args)

            messages.append(Message(role="assistant", content=completion["content"]))

            messages.append(
                Message(
                    role="system",
                    content="That was not a function call. Please call a function.",
                )
            )

        return None

    async def digit_completions(
        self,
        query_messages: List[List[Message]],
    ) -> List[int]:
        completions = [
            self._digit_completion_with_retries(query_message)
            for query_message in query_messages
        ]

        return await asyncio.gather(*completions)

    async def digit_completion(self, query: str) -> int:
        return await self._digit_completion_with_retries(
            messages=[Message(role="user", content=query)]
        )

    async def embed(self, query: str) -> List[float]:
        return (
            await self._client.embeddings.create(  # type: ignore
                input=query, model="text-embedding-ada-002"
            )
        ).data[0].embedding

    @property
    def embedding_size(self) -> int:
        return self._embedding_size
    
    async def Close(self):
        await self._client.close()

    async def _digit_completion_with_retries(self, messages: List[Message]) -> int:
        for _ in range(3):
            text = str(
                (
                    await self._client.chat.completions.create(  # type: ignore
                        model=self._model,
                        messages=_parse_messages_arry(messages),
                        temperature=0,
                        max_tokens=1,
                    )
                ).choices[0].message.content
            )

            # TODO: error handle
            match = re.search(r"\d", text)
            if match:
                return int(match.group())

            messages.append(Message(role="assistant", content=text))

            messages.append(
                Message(
                    role="system",
                    content="That was not a digit. Try again.",
                )
            )

        return -1


def _parse_messages_arry(
    messages: List[Message],
) -> Any:
    return [
        {
            "role": msg.role,
            "content": msg.content,
        }
        for msg in messages
    ]

# def _parse_messages(
#     messages: List[Message],
# ) -> List[Dict[str, str]]:
#     return [msg.dict() for msg in messages]


# We need to do this because empty array [] is not valid for functions arg
# in OpenAI client. So if it's empty we need to not include it.
# def _generate_completions_function_args(
#     functions: List[Dict[str, str]]
# ) -> Dict[str, List[Dict[str, str]]]:
#     if len(functions) > 0:
#         chat_function_arguments = dict(
#             functions=functions,
#         )
#         return chat_function_arguments
#     return {}
