from fastapi import FastAPI, APIRouter, Depends, UploadFile, status, Request
from fastapi.responses import JSONResponse
import os
from helpers.config import get_settings, Settings
from controllers import DataController, ProjectController, ProcessController
from models import ResponseSignal, ProjectModel, ChunkModel, AssetModel
from .schemes import ProcessRequest
import aiofiles
import logging
from models import Chunk, Asset
from models import AssetEnum
from controllers import NLPController
from models import MessageModel, ConversationModel
from .schemes.data import Asset_config

logger = logging.getLogger("uvicorn.error")

data_router = APIRouter(
    prefix="/api/v1/data",
    tags=["api_v1", "data"],
)

@data_router.post("/upload/{project_id}")
async def upload_data(request: Request, project_id: int, file: UploadFile, 
                      app_settings: Settings = Depends(get_settings)):


    project_model = await ProjectModel.create_instance(
         db_client=request.app.db_client
    )
    project = await project_model.get_project_or_create_one(project_id=project_id)


    # validate the file extensions
    data_controller = DataController()

    is_valid, signal = data_controller.validate_uploaded_file(file=file)

    if not is_valid:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content = {
                "signal": signal
            }
        )

    project_controller = ProjectController()
    project_dir_path = project_controller.get_project_path(project_id=project_id)
    file_path, file_id = data_controller.generate_unique_filepath(
        orig_file_name=file.filename,
        project_id=project_id
    )

    try:

        async with aiofiles.open(file_path, "wb") as f:

            while chunk := await file.read(app_settings.FILE_DEFAULT_CHUNK_SIZE):
                await f.write(chunk)

    except Exception as e:
            logger.error(f"Error while uploading a file {e}")
            return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content = {
                        "signal": ResponseSignal.FILE_UPLOADED_FAIL.value
                    }
                )

    asset_model = await AssetModel.create_instance(
            db_client=request.app.db_client
    )
    asset_resource = Asset(
    asset_project_id=project.project_id,
    asset_type=AssetEnum.FILE.value,
    asset_name=file_id,
    asset_size=os.path.getsize(file_path),
    asset_config=Asset_config
)
    asset = await asset_model.insert_asset(asset=asset_resource)


    return JSONResponse(
                content = {
                    "signal": ResponseSignal.FILE_UPLOADED_SUCCESS.value,
                    "file_id" : str(asset.asset_id)
                }
            )


@data_router.post("/process/{project_id}")
async def process_endpoint(request: Request, project_id: int, process_request: ProcessRequest):

     
     process_controller = ProcessController(
          project_id=project_id,
          vision_model=request.app.vision_client, 
          ocr_client=request.app.ocr_client
     )
     
     do_reset = process_request.do_reset

     project_model = await ProjectModel.create_instance(
          db_client=request.app.db_client
     )

     project = await project_model.get_project_or_create_one(
           project_id=project_id
     )

     asset_model = await AssetModel.create_instance(
                                db_client=request.app.db_client
     )

     project_files_ids = {}
     if process_request.file_id:
          asset_record = await asset_model.get_asset_record(
                asset_project_id=project.project_id,
                asset_name=process_request.file_id
          )

          if asset_record is None:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content = {
                        "signal": ResponseSignal.FILE_ID_ERROR.value
                    }
                )
                
          project_files_ids = {
                asset_record.asset_id: asset_record.asset_name
          }

     else:

           project_files = await asset_model.get_all_project_assets(
                asset_project_id=project.project_id,
                asset_type=AssetEnum.FILE.value
           )

           project_files_ids = {rec.asset_id:rec.asset_name for rec in project_files}

     if len(project_files_ids) == 0:
          return JSONResponse(
               status_code=status.HTTP_400_BAD_REQUEST,
                content = {
                    "signal": ResponseSignal.NO_FILES_ERROR.value
                }
            )


     chunk_model = await ChunkModel.create_instance(
               db_client=request.app.db_client
          )

     message_model = await MessageModel.create_instance(
             db_client=request.app.db_client
         )
     
     conversation_model = await ConversationModel.create_instance(
             db_client=request.app.db_client
         )

     nlp_controller = NLPController(
             vectordb_client=request.app.vectordb_client,
             generation_client=request.app.generation_client,
             embedding_client=request.app.embedding_client,
             template_parser=request.app.template_parser,
             reranker_client=request.app.reranker_client,
             message_model=message_model,
             lightweight_client=request.app.ligthweigth_client,
             conversation_model=conversation_model,
             vision_client=request.app.vision_client 
     )

     if do_reset:

        collection_name = nlp_controller.create_collection_name(
             project_id=project.project_id
        )

        _ = await request.app.vectordb_client.delete_collection(
             collection_name = collection_name
        )

        _ = await chunk_model.delete_chunks_by_project_id(
                project_id=project.project_id
        )



     no_records=0
     no_files = len(project_files_ids)

     for asset_id, file_id in project_files_ids.items():  

        file_chunks = await process_controller.process_file_content(
            file_id=file_id,
            chunk_size=process_request.chunk_size,
            overlap_size=process_request.overlap_size,
        )

        if file_chunks is None:
              continue

        if file_chunks is None or len(file_chunks) == 0:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content = {
                    "signal": ResponseSignal.FILE_PROCESSED_FAIL.value
                }
            )


        file_chunks_records = [Chunk(
            chunk_text = chunk.page_content,
            chunk_metadata = chunk.metadata,
            chunk_order = idx + 1,
            chunk_project_id = project.project_id,
            chunk_asset_id =  asset_id
        ) for idx, chunk in enumerate(file_chunks)]


        no_records += await chunk_model.insert_many_chunks(
            chunks=file_chunks_records,
        )

     
     return JSONResponse(
            content = {
                "signal": ResponseSignal.FILE_PROCESSED_SUCCESS.value,
                "inserted_chunks" : no_records,
                "processed_files": no_files
            }
        )


   




        