from fastapi import APIRouter, Depends, Response, status, HTTPException, Request
from fastapi.responses import StreamingResponse, HTMLResponse
from typing import Optional, List
import hashlib
import os
from services.qr_generator import gen_qr_code

from models.reports import Report, ReportCreate, ReportUpdate
from models.users import User
from services.users import get_current_user
from services.depends import get_report_service, get_users_service
from services.reports import ReportsService
from services.users import UsersService

router = APIRouter(
    prefix="/reports",
    tags=['reports'])


#@router.get("/{id}", response_model=Report)
#async def get_report(id: str, service: ReportsService = Depends(get_report_service)):
    #"""Просмотр данных отчета по id"""
    #return await service.get(id)


@router.post("/", response_model=Report)
async def create_report(laboratory_number: str, test_type: str, report_data: ReportCreate,
                        user: User = Depends(get_current_user), service: ReportsService = Depends(get_report_service)):
    """Создание отчета"""
    if not user.active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is not active",
            headers={"WWW-Authenticate": "Bearer"},
        )

    id = hashlib.sha1(
        f"{report_data.object_number} {laboratory_number} {test_type} {user.id}".encode("utf-8")).hexdigest()

    return await service.create(report_id=id, user_id=user.id, report_data=report_data)


@router.post("/qr")
def create_qr(id: str, user: User = Depends(get_current_user)):
    """Создание qr"""
    if not user.active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is not active",
            headers={"WWW-Authenticate": "Bearer"},
        )
    text = f"https://georeport.ru/report/?id={id}"

    path_to_download = os.path.join("services", "digitrock_qr.png")  # Путь до фона qr кода

    file = gen_qr_code(text, path_to_download)
    return StreamingResponse(file, media_type="image/png")


@router.post("/report_and_qr")
async def create_report_and_qr(laboratory_number: str, test_type: str, report_data: ReportCreate,
                        user: User = Depends(get_current_user), service: ReportsService = Depends(get_report_service)):
    """Создание отчета"""
    if not user.active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is not active",
            headers={"WWW-Authenticate": "Bearer"},
        )

    id = hashlib.sha1(
        f"{report_data.object_number} {laboratory_number} {test_type} {user.id}".encode("utf-8")).hexdigest()

    await service.create(report_id=id, user_id=user.id, report_data=report_data)

    if not user.active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is not active",
            headers={"WWW-Authenticate": "Bearer"},
        )
    text = f"https://georeport.ru/report/?id={id}"

    path_to_download = os.path.join("services", "digitrock_qr.png")  # Путь до фона qr кода

    file = gen_qr_code(text, path_to_download)
    return StreamingResponse(file, media_type="image/png")


@router.put("/{id}", response_model=Report)
async def update_report(id: str, report_data: ReportUpdate,
                        user: User = Depends(get_current_user),
                        service: ReportsService = Depends(get_report_service)):
    """Обновление отчета"""
    if not user.active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is not active",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return await service.update(id=id, user_id=user.id, report_data=report_data)


@router.delete('/{id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(id: str, user: User = Depends(get_current_user),
                        service: ReportsService = Depends(get_report_service)):
    """Удаление отчета"""
    await service.delete(id=id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/objects/{object_number}", response_model=Optional[List[Report]])
async def get_object(object_number: str,
                      user: User = Depends(get_current_user),
                      service: ReportsService = Depends(get_report_service)):
    """Просмотр отчетов по объекту"""
    return await service.get_object(user_id=user.id, object_number=object_number, is_superuser=user.is_superuser)


@router.get("/objects/", response_model=List)
async def get_objects(user: User = Depends(get_current_user),
                      service: ReportsService = Depends(get_report_service)):
    """Просмотр всех объектов пользователя"""
    return await service.get_objects(user_id=user.id)


@router.post("/objects/{object_number}/{activate}")
async def activate_deactivate_object(object_number: str, active: bool,
                     user: User = Depends(get_current_user),
                     service: ReportsService = Depends(get_report_service)):
    """Активация и деактивация объекта"""
    reports = await service.get_object(user_id=user.id, object_number=object_number, is_superuser=user.is_superuser)
    if reports:
        for report in reports:
            report.active = active

        await service.update_many(id=report.id, reports=reports)
    return {"massage": f"{len(reports)} reports from object {object_number} is {'activate' if active else 'deactivate'}"}
