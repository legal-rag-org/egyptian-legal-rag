import logging

from models.db_schemes.insurance_rag.schemes import UserMemory 

from .schemes.MemoryConsolidation import MemoryConsolidationAction, MemoryConsolidationResponse

class UserMemoryService:

    ALLOWED_MEMORY_TYPES = {
        "preference",
        "goal",
        "project",
        "fact",
        "constraint",
    }

    def __init__(self, memory_model, embedding_client):
        self.memory_model = memory_model
        self.embedding_client = embedding_client

        self.logger = logging.getLogger("uvicorn")

    async def create_memory(
        self,
        user_id: int,
        content: str,
        memory_type: str,
        importance: int = 3,
        source_conversation_id: int | None = None,
    ):

        content = content.strip()

        if not content:
            raise ValueError("Memory content cannot be empty")

        if memory_type not in self.ALLOWED_MEMORY_TYPES:
            raise ValueError("Invalid memory type")

        if not 1 <= importance <= 5:
            raise ValueError("Importance must be between 1 and 5")

        embedding = await self.embedding_client.embed_text(content)

        if embedding is None:
            raise RuntimeError("Failed to generate memory embedding")

        if len(embedding) != self.embedding_client.embedding_size:
            raise ValueError("Invalid embedding dimension")

        memory = UserMemory(
            content=content,
            embedding=embedding,
            memory_type=memory_type,
            importance=importance,
            memory_user_id=user_id,
            source_conversation_id=source_conversation_id,
        )

        return await self.memory_model.insert_memory(memory)


    
    async def create_many_memories(
        self,
        user_id: int,
        memories: list[dict],
        source_conversation_id: int | None = None,
    ):
        if not memories:
            return []

        contents = []

        for memory in memories:
            content = memory.get("content", "")

            if not isinstance(content, str):
                raise ValueError("Memory content must be a string")

            content = content.strip()
            memory_type = memory.get("memory_type")
            importance = memory.get("importance", 3)

            if not content:
                raise ValueError("Memory content cannot be empty")

            if memory_type not in self.ALLOWED_MEMORY_TYPES:
                raise ValueError(f"Invalid memory type: {memory_type}")

            if (
                not isinstance(importance, int)
                or isinstance(importance, bool)
                or not 1 <= importance <= 5
            ):
                raise ValueError("Importance must be an integer between 1 and 5")

            contents.append(content)

        embeddings = await self.embedding_client.embed_text(contents)

        if embeddings is None:
            raise RuntimeError("Failed to generate memory embeddings")

        if len(embeddings) != len(memories):
            raise ValueError("Embedding count does not match memory count")

        embedding_size = self.embedding_client.embedding_size

        if any(len(embedding) != embedding_size for embedding in embeddings):
            raise ValueError("Invalid embedding dimension")

        memory_objects = []

        for memory_data, content, embedding in zip(
            memories,
            contents,
            embeddings,
        ):
            memory = UserMemory(
                content=content,
                embedding=embedding,
                memory_type=memory_data["memory_type"],
                importance=memory_data.get("importance", 3),
                memory_user_id=user_id,
                source_conversation_id=(
                    memory_data.get("source_conversation_id")
                    or source_conversation_id
                ),
            )

            memory_objects.append(memory)

        await self.memory_model.insert_many_memories(
            memories=memory_objects,
        )

        return memory_objects


        
    async def update_memory(
        self,
        memory_id: int,
        user_id: int,
        content: str | None = None,
        memory_type: str | None = None,
        importance: int | None = None,
    ):
        update_data = {}

        # Validate and process content
        if content is not None:
            if not isinstance(content, str):
                raise ValueError("Memory content must be a string")

            content = content.strip()

            if not content:
                raise ValueError("Memory content cannot be empty")

            embedding = await self.embedding_client.embed_text(content)

            if embedding is None:
                raise RuntimeError("Failed to generate memory embedding")

            if len(embedding) != self.embedding_client.embedding_size:
                raise ValueError("Invalid embedding dimension")

            update_data["content"] = content
            update_data["embedding"] = embedding

        # Validate memory type
        if memory_type is not None:
            if memory_type not in self.ALLOWED_MEMORY_TYPES:
                raise ValueError("Invalid memory type")

            update_data["memory_type"] = memory_type

        # Validate importance
        if importance is not None:
            if (
                not isinstance(importance, int)
                or isinstance(importance, bool)
                or not 1 <= importance <= 5
            ):
                raise ValueError("Importance must be an integer between 1 and 5")

            update_data["importance"] = importance

        # Nothing to update
        if not update_data:
            return False

        return await self.memory_model.update_memory(
            memory_id=memory_id,
            user_id=user_id,
            **update_data,
        )


    async def get_memories(
        self,
        user_id: int,
        query: str,
        top_k: int = 5,
        max_distance: float | None = None,
    ):
        if not isinstance(query, str) or not query.strip():
            raise ValueError("Query cannot be empty")

        if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 1:
             raise ValueError("top_k must be a positive integer")

        query = query.strip()

        query_embedding = await self.embedding_client.embed_text(query)

        if query_embedding is None:
            raise RuntimeError("Failed to generate query embedding")

        if len(query_embedding) != self.embedding_client.embedding_size:
            raise ValueError("Invalid embedding dimension")

        memories = await self.memory_model.search_similar_memories(
            user_id=user_id,
            query_embedding=query_embedding,
            top_k=top_k,
            max_distance=max_distance
        )

        return memories

    async def deactivate_memory(
        self,
        memory_id: int,
        user_id: int,
    ):
        return await self.memory_model.deactivate_memory(
            memory_id=memory_id,
            user_id=user_id,
        )

    
    async def delete_memory(
        self,
        memory_id: int,
        user_id: int,
    ):
        return await self.memory_model.delete_memory(
            memory_id=memory_id,
            user_id=user_id,
        )

    
    async def get_memory_by_id(
        self,
        memory_id: int,
        user_id: int,
    ):
        return await self.memory_model.get_memory_by_id(
            memory_id=memory_id,
            user_id=user_id,
        )

    
    async def get_memories_by_user(
        self,
        user_id: int,
        page_no: int = 1,
        page_size: int = 50,
        active_only: bool = True,
    ):
        if page_no < 1:
            raise ValueError("page_no must be >= 1")

        if not 1 <= page_size <= 100:
            raise ValueError("page_size must be between 1 and 100")

        return await self.memory_model.get_memories_by_user(
            user_id=user_id,
            page_no=page_no,
            page_size=page_size,
            active_only=active_only,
        )

        
    async def get_total_memories_count(
        self,
        user_id: int,
        active_only: bool = True,
    ):
        return await self.memory_model.get_total_memories_count(
            user_id=user_id,
            active_only=active_only,
        )


    async def apply_consolidation_decision(
        self,
        user_id: int,
        new_memory: dict,
        decision: MemoryConsolidationResponse,
        source_conversation_id: int | None = None,
    ):

        # Step 1: Validate inputs

        if not isinstance(new_memory, dict):
            raise ValueError("New memory must be a dictionary")

        if not isinstance(decision, MemoryConsolidationResponse):
            raise TypeError("Invalid consolidation decision")

        content = new_memory.get("content")
        memory_type = new_memory.get("memory_type")
        importance = new_memory.get("importance", 3)

        if not isinstance(content, str) or not content.strip():
            raise ValueError("Memory content cannot be empty")

        content = content.strip()

        if memory_type not in self.ALLOWED_MEMORY_TYPES:
            raise ValueError("Invalid memory type")

        if (
            not isinstance(importance, int)
            or isinstance(importance, bool)
            or not 1 <= importance <= 5
        ):
            raise ValueError("Importance must be an integer between 1 and 5")

        if source_conversation_id is None:
            source_conversation_id = new_memory.get(
                "source_conversation_id"
            )

        action = decision.action

        # Step 2: INSERT

        if action == MemoryConsolidationAction.INSERT:

            saved_memory = await self.create_memory(
                user_id=user_id,
                content=content,
                memory_type=memory_type,
                importance=importance,
                source_conversation_id=source_conversation_id,
            )

            return {
                "action": action.value,
                "memory": saved_memory,
            }

        # Step 3: Retrieve and verify target memory ownership

        target_memory = await self.get_memory_by_id(
            memory_id=decision.target_memory_id,
            user_id=user_id,
        )

        if target_memory is None:
            raise ValueError(
                "Target memory does not exist or does not belong to this user"
            )

        # Step 4: UPDATE

        if action == MemoryConsolidationAction.UPDATE:
            updated = await self.update_memory(
                memory_id=decision.target_memory_id,
                user_id=user_id,
                content=decision.updated_content,
            )

            if not updated:
                raise RuntimeError("Failed to update target memory")

            updated_memory = await self.get_memory_by_id(
                memory_id=decision.target_memory_id,
                user_id=user_id,
            )

            if updated_memory is None:
                raise RuntimeError("Updated memory could not be retrieved")

            return {
                "action": action.value,
                "memory": updated_memory,
            }

        # Step 5: REINFORCE

        if action == MemoryConsolidationAction.REINFORCE:
            new_importance = min(target_memory.importance + 1, 5)

            updated = await self.update_memory(
                memory_id=decision.target_memory_id,
                user_id=user_id,
                importance=new_importance,
            )

            if not updated:
                raise RuntimeError("Failed to reinforce target memory")

            reinforced_memory = await self.get_memory_by_id(
                memory_id=decision.target_memory_id,
                user_id=user_id,
            )

            if reinforced_memory is None:
                raise RuntimeError("Reinforced memory could not be retrieved")

            return {
                "action": action.value,
                "memory": reinforced_memory,
            }

        # Step 6: SKIP

        if action == MemoryConsolidationAction.SKIP:

            return {
                "action": action.value,
                "memory": target_memory,
            }

        # Step 7: CONFLICT

        if action == MemoryConsolidationAction.CONFLICT:

            conflicting_memory = await self.create_memory(
                user_id=user_id,
                content=content,
                memory_type=memory_type,
                importance=importance,
                source_conversation_id=source_conversation_id,
            )

            return {
                "action": action.value,
                "memory": conflicting_memory,
                "conflicting_memory_id": target_memory.memory_id,
            }

        raise ValueError(f"Unsupported consolidation action: {action}")




