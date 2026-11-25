from fastapi import (
    APIRouter,
    Request,
    Depends,
    HTTPException,
    Query,
    status
)

from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from utils.auth import get_current_user

from models import AgentExecutionModel, AgentStepModel
from controllers.AgentExecutionController import AgentExecutionController

import uuid

from routes.schemes.agent_execution import AgentExecutionResponse, AgentStepResponse
from models.Enums import ResponseSignal



agent_execution_router = APIRouter(
    prefix="/api/v1/agent-executions",
    tags=["api_v1", "agent-executions"]
)



@agent_execution_router.get("/")
async def get_executions(
    request: Request,

    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),

    conversation_uuid: uuid.UUID | None = Query(None),

    status: str | None = Query(
        None,
        pattern="^(running|completed|failed)$"
    ),

    current_user=Depends(get_current_user),
):

    # Initialize Models
    agent_execution_model = await AgentExecutionModel.create_instance(
        db_client=request.app.db_client
    )

    agent_step_model = await AgentStepModel.create_instance(
        db_client=request.app.db_client
    )

    # Initialize Controller
    agent_execution_controller = AgentExecutionController(
        agent_execution_model=agent_execution_model,
        agent_step_model=agent_step_model,
    )

    # Get Executions
    result = await agent_execution_controller.get_executions_by_user(
        user_id=current_user.user_id,
        page=page,
        page_size=page_size,
        status=status,
        conversation_uuid=conversation_uuid,
    )

    return jsonable_encoder(result)



@agent_execution_router.get(
    "/{execution_uuid}",
    response_model=AgentExecutionResponse,
)
async def get_execution(
    request: Request,
    execution_uuid: uuid.UUID,
    current_user=Depends(get_current_user),
):

    agent_execution_model = await AgentExecutionModel.create_instance(
        db_client=request.app.db_client
    )

    agent_step_model = await AgentStepModel.create_instance(
        db_client=request.app.db_client
    )

    agent_execution_controller = AgentExecutionController(
        agent_execution_model=agent_execution_model,
        agent_step_model=agent_step_model,
    )

    execution = await agent_execution_controller.get_execution_by_uuid(
        execution_uuid=execution_uuid,
        user_id=current_user.user_id,
    )

    if execution is None:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignal.EXECUTION_NOT_FOUND.value,
            }
        )

    return execution




@agent_execution_router.get(
    "/{execution_uuid}/steps",
    response_model=list[AgentStepResponse],
)
async def get_execution_steps(
    request: Request,
    execution_uuid: uuid.UUID,
    current_user=Depends(get_current_user),
):

    agent_execution_model = await AgentExecutionModel.create_instance(
        db_client=request.app.db_client
    )

    agent_step_model = await AgentStepModel.create_instance(
        db_client=request.app.db_client
    )

    agent_execution_controller = AgentExecutionController(
        agent_execution_model=agent_execution_model,
        agent_step_model=agent_step_model,
    )

    steps = await agent_execution_controller.get_execution_steps(
        execution_uuid=execution_uuid,
        user_id=current_user.user_id,
    )

    if steps is None:
        return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "signal": ResponseSignal.STEPS_NOT_FOUND.value,
                    }
                )

    return steps
