from .BaseDataModel import BaseDataModel
from models import Project
from sqlalchemy import func, select

class ProjectModel(BaseDataModel):
    def __init__(self, db_client : object):
        super().__init__(db_client=db_client)


    @classmethod
    async def create_instance(cls, db_client: object):
         instance = cls(db_client)
         return instance

    

    async def insert_project(self, project: Project):
        async with self.db_client() as session:
            async with session.begin():
                session.add(project)

            await session.refresh(project)

        return project


    async def get_project_or_create_one(self, project_id: int):

        async with self.db_client() as session:
            async with session.begin():

                search_stmt = select(Project).where(
                     Project.project_id == project_id
                )

                result = await session.execute(search_stmt)
                project = result.scalar_one_or_none()

                if project is None:
                    project = Project(
                        project_id=project_id
                    )
                    session.add(project)

            await session.refresh(project)

            return project

    async def get_all_projects(self, page_no: int = 1, page_size: int = 10):

        if page_no < 1:
            raise ValueError("page_no must be >= 1")

        if not 1 <= page_size <= 100:
            raise ValueError("page_size must be between 1 and 100")

        async with self.db_client() as session:
            
            # total number of projects
            count_stmt = select(
                 func.count(Project.project_id)
            )
            result = await session.execute(count_stmt)

            total_projects = result.scalar_one()

            total_pages = total_projects // page_size
            if total_projects % page_size > 0:
                total_pages += 1

            query = select(Project).offset((page_no - 1) * page_size).limit(page_size)
            result = await session.execute(query)
            projects = result.scalars().all()


            return projects, total_projects, total_pages

    
        
