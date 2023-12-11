import logging
import asyncio
from typing import List, Optional, Tuple, Union
import re
import numpy as np

from pydantic import UUID4

from game.memory import GenAgentMemory
from game.prompt_helpers import (
    clean_response,
    generate_functions_from_actions,
    generate_tools_from_actions,
    get_action_messages,
    get_chat_messages,
    get_guardrail_query,
    get_interact_messages,
    get_query_messages,
    get_rate_function,
    rating_to_int,
)
from llm.openai import OpenAIInterface

#from openai.embeddings_utils import cosine_similarity

from schema import ActionCompletion, Conversation, Knowledge, Memory, Message


class GenAgent:
    def __init__(
        self,
        knowledge: Knowledge,
        memory: GenAgentMemory,
    ):
        """Should never be called directly. Use create() instead."""
        self._memory = memory
        self._conversation_history: List[Message] = []
        self._knowledge = knowledge
        self._conversation_context = Conversation()

    @classmethod
    async def create(
        cls, knowledge: Knowledge, memory: GenAgentMemory
    ):
        agent = cls(knowledge, memory)
        await agent._fill_memories()
        return agent

    async def _fill_memories(self):
        initial_memories = [
            lore.memory
            for lore in self._knowledge.shared_lore
            if self._knowledge.agent_def.uuid in lore.known_by
        ]

        for memory in self._knowledge.agent_def.personal_lore:
            memory.isPersenal = True

        initial_memories += self._knowledge.agent_def.personal_lore

        awaitables = [self._memory.add_memory(memory) for memory in initial_memories]
        await asyncio.gather(*awaitables)

    @property
    def uuid(self) -> UUID4:
        return self._knowledge.agent_def.uuid

    @property
    def name(self) -> str:
        return self._knowledge.agent_def.name

    async def add_memory(self, memory: Memory) -> None:
        await self._memory.add_memory(memory)

    async def interact(
        self, message: Optional[str]
    ) -> Tuple[Union[Message, ActionCompletion], List[Message]]:
        if message:
            self._conversation_history.append(Message(role="user", content=message))

        memories = await self._queryMemories(message)

        messages = get_interact_messages(
            self._knowledge,
            self._conversation_context,
            memories,
            self._conversation_history,
        )

        self._debugMessage(messages)

        openAI = OpenAIInterface()

        tools = generate_tools_from_actions(self._knowledge.agent_def.actions)
        completion = await openAI.completion(messages, tools)

        if isinstance(completion, Message):
            self._conversation_history.append(clean_response(self.name, completion))
            # process each message in messages
            completion.content = self._processKeywords(completion.content, memories)

        return completion, messages

    async def chat(self, message: str) -> Tuple[Message, List[Message]]:
        self._conversation_history.append(Message(role="user", content=message))

        memories = await self._queryMemories(message)

        messages = get_chat_messages(
            self._knowledge,
            self._conversation_context,
            memories,
            self._conversation_history,
        )

        openAI = OpenAIInterface()

        completion = await openAI.chat_completion(messages)
        # process each message in messages
        completion.content = self._processKeywords(completion.content, memories)

        self._conversation_history.append(clean_response(self.name, completion))
        return completion, messages

    async def act(
        self, message: Optional[str]
    ) -> Tuple[Optional[ActionCompletion], List[Message]]:
        if message:
            self._conversation_history.append(Message(role="user", content=message))

        memories = await self._queryMemories(message)

        messages = get_action_messages(
            self._knowledge,
            self._conversation_context,
            memories,
            self._conversation_history,
        )
        functions = generate_functions_from_actions(self._knowledge.agent_def.actions)

        openAI = OpenAIInterface()

        return (
            await openAI.action_completion(messages, functions),
            messages,
        )

    async def query(self, queries: List[str]) -> List[int]:
        """Returns a numerical answer to queries into the Agent's
        thoughts and emotions. 1 = not at all, 5 = extremely
        Ex. How happy are you given this conversation? -> 3 (moderately)"""
        memories = await asyncio.gather(
            *[self._queryMemories(query) for query in queries]
        )

        query_messages = get_query_messages(
            self._knowledge,
            self._conversation_context,
            memories,
            self._conversation_history,
            queries,
        )

        functions = [get_rate_function()]
        openAI = OpenAIInterface()
        awaitables = [
            openAI.action_completion(msgs, functions)
            for msgs in query_messages
        ]
        ratings = await asyncio.gather(*awaitables)

        return [rating_to_int(rating) for rating in ratings]

    async def guardrail(self, message: str) -> int:
        """Is `message` something that the LLM thinks the GenAgent might say?
        Useful for playable characters and not letting players say inappropriate or
        anachronistic things.
        """
        guardrail_query = get_guardrail_query(self._knowledge, message)

        query_messages = get_query_messages(
            self._knowledge,
            self._conversation_context,
            [[]],
            self._conversation_history,
            [guardrail_query],
        )

        functions = [get_rate_function()]
        openAI = OpenAIInterface()
        completion = await openAI.action_completion(
            query_messages[0], functions
        )

        return rating_to_int(completion)
    
    def _processKeywords(
            self, 
            message:str,
            memorys:List[Memory]
        ) -> str:
    
        for memory in memorys:
            if memory.keywords is None:
                continue
            
            for keyword in memory.keywords:
                if keyword in message:
                    message = message.replace(keyword, '[keyword]' + keyword + '[/keyword]')

        return message
    
    async def _processMessage(
            self,
            content:str
        ):
        # TODO: this is a hacky way to do this, but it works for now
        sentances = re.split(r'([,.I?，。！？])', content)
        # sentances:List[str] = []
        # sentances.append(content)

        for msg in sentances:

            # msg is too short to be a meanning full sentance
            if len(msg) <= 3:
                continue

            logger = logging.getLogger()
            logger.debug('Sentence:' + msg)
            #get embed of this msg from llm
            openAI = OpenAIInterface()
            msg_embed = await openAI.embed(msg)

            retrived_memories:List[Memory] = []
            retrived_memories = await self._memory.retrieve_relevant_memories(
                [Memory(description=msg, embedding=msg_embed)], 
                self._conversation_context.memories_to_include
                )

            for memory in retrived_memories:

                if memory.embedding is None:
                    memory.embedding = await openAI.embed(memory.description)

                similarity = self._cosineSimilarity(memory.embedding, msg_embed)
                distance = self._distanceFromEmbedding(memory.embedding, msg_embed)

                loreID = ""
                if memory.client_id is not None:
                    loreID = memory.client_id

                logger.debug('LoreID ' + loreID + ':' + memory.description + ' Similarity:' + str(similarity) + ' Distance:' + str(distance))
                #if(similarity > 0.95):
                #    msg = '<LORE ' + 'ID=' + lore.client_id + ' >' + msg + '</LORE>'
                #    break

        return content
    
    def _distanceFromEmbedding(self, memory:Optional[List[float]] = None, message:Optional[List[float]] = None):
        if memory is None:
            logger = logging.getLogger()
            logger.warn("memory embedding is None")
            return 0
        
        if message is None:
            logger = logging.getLogger()
            logger.warn("message embedding is None")
            return 0
        
        return np.linalg.norm(np.subtract(memory, message))
    
    def _cosineSimilarity(self, memory:Optional[List[float]] = None, message:Optional[List[float]] = None):

        if memory is None:
            logger = logging.getLogger()
            logger.warn("memory embedding is None")
            return 0
        
        if message is None:
            logger = logging.getLogger()
            logger.warn("message embedding is None")
            return 0

        return np.dot(memory, message) / (np.linalg.norm(memory) * np.linalg.norm(memory))
    
    def _debugMessage(self, msg:List[Message]):
        logger = logging.getLogger()
        logger.info("GPT Message:")
        for m in msg:
            logger.info("Role:" + m.role)
            logger.info("Content:" + m.content)

    def startConversation(
        self,
        conversation: Conversation,
        history: List[Message],
    ):
        self._conversation_context = conversation
        self._conversation_history = history

    def resetConversation(self):
        self._conversation_history = []

    # TODO: use setter?
    def updateKnowledge(self, knowledge: Knowledge):
        # TODO: this doesn't update their memories, but we also don't really
        # want to overwrite what exists. Not sure what to do here.
        self._knowledge = knowledge

    async def _queryMemories(
        self, message: Optional[str] = None, max_memories: Optional[int] = None
    ):
        if not max_memories:
            max_memories = self._conversation_context.memories_to_include

        queries: List[Memory] = []

        context_description = None

        if message:
            queries.append(Memory(description=message))
            context_description = (self._conversation_context.scene_description or "") + (
            self._conversation_context.instructions or ""
        )
            
        if context_description:
            queries.append(Memory(description=context_description))

        return await self._memory.retrieve_relevant_memories(queries, top_k=max_memories)
        
    async def _queryMemoriesDesc(
            self, message: Optional[str] = None, max_memories: Optional[int] = None
    ):
        return [ memory.description for memory in await  self._queryMemories() ]
