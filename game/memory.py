import logging
from typing import Dict, List, Optional

from game.ti_retriever import TIRetriever
from llm.openai import OpenAIInterface

# from eastworld.wrappers.openai
from schema import Memory, Message

_MEM_IMPORTANCE_TMPL = """On the scale of 0 to 9, where 0 is purely mundane"
(e.g., brushing teeth, making bed) and 9 is
extremely poignant (e.g., a break up, college
acceptance), rate the likely poignancy of the
following piece of memory. Respond with a single integer without
explanation.
\nMemory: {memory_content}
\nRating: """


class GenAgentMemory:
    # TODO: make LLM configurable
    def __init__(
        self,
        default_num_memories_returned: int,
        retriever: TIRetriever,
    ):
        self._default_num_memories_returned = default_num_memories_returned
        self._retriever = retriever

    async def add_memory(self, memory: Memory) -> None:
        # TODO: parallelize
        if memory.importance == 0:
            memory.importance = await self._rate_importance(memory)
        if not memory.embedding:
            openAI = OpenAIInterface()
            memory.embedding = await openAI.embed(memory.description)

        self._retriever.add_memory(memory)

    def get_all_memory(self) -> List[Memory]:
        return self._retriever.get_all_memory()

    async def retrieve_relevant_memories(
        self, queries: List[Memory], top_k: Optional[int]
    ) -> List[Memory]:
        if not top_k:
            top_k = self._default_num_memories_returned

        # TODO: remember CS170 and find a faster alg for this
        # TODO: also gather awaits instead
        memory_to_max_importance: Dict[str, float] = dict()
        # TODO: fix this lol
        memory_desc_to_memory: Dict[str, Memory] = dict()

        for query in queries:
            if not query.embedding:
                openAI = OpenAIInterface()
                query.embedding = await openAI.embed(query.description)

            top_k_for_query = self._retriever.get_relevant_memories(query, top_k)
            for memory, score in top_k_for_query:
                memory_to_max_importance[memory.description] = max(
                    memory_to_max_importance.get(memory.description, 0), score
                )
                memory_desc_to_memory[memory.description] = memory

        vals = list(memory_to_max_importance.items())
        vals.sort(key=lambda x: -x[1])

        logger = logging.getLogger()
        logger.debug("Pulled memories: \n")
        logger.debug("\n".join([f"{desc}: {val}" for desc, val in vals]))

        return [memory_desc_to_memory[desc] for desc, _ in vals[:top_k]]

    async def _rate_importance(self, memory: Memory) -> int:
        message = Message(
            role="user",
            content=_MEM_IMPORTANCE_TMPL.format(memory_content=memory.description),
        )
        openAI = OpenAIInterface()
        return (await openAI.digit_completions([[message]]))[0] + 1
