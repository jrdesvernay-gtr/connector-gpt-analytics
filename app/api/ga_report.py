"""GA4 report query endpoint for Custom GPT."""

import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.api.dependencies import get_valid_gpt_token
from app.schemas.ga import GAReportRequest, GAReportResponse
from app.services.ga_service import GAService
from app.models.ga_connection import GAConnection
from app.models.query_log import QueryLog
from app.core.errors import GAPropertyNotFoundError, OAuthTokenRevokedError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/ga/run-report", response_model=GAReportResponse)
async def run_ga_report(
    report_request: GAReportRequest,
    token_data: dict = Depends(get_valid_gpt_token),
    db: Session = Depends(get_db),
):
    """
    Run a GA4 report query.
    
    This endpoint is protected by GPT OAuth and requires a valid access token
    in the Authorization header. It fetches GA4 data for the user's workspace.
    
    Args:
        report_request: GA report request with metrics, dimensions, date ranges
        token_data: GPT token data (from dependency) containing workspace and gpt_token
        db: Database session
        
    Returns:
        GA report response with rows, totals, and row count
    """
    workspace = token_data["workspace"]
    gpt_token = token_data["gpt_token"]
    
    logger.info(
        f"GA report request for workspace {workspace.id} "
        f"(metrics: {report_request.metrics}, dimensions: {report_request.dimensions})"
    )
    
    # Get GA connection for workspace
    property_id = report_request.property_id
    if property_id:
        # Use specified property
        ga_connection = (
            db.query(GAConnection)
            .filter(
                GAConnection.workspace_id == workspace.id,
                GAConnection.property_id == property_id,
            )
            .first()
        )
    else:
        # Use workspace's default GA connection - use most recently updated/created
        ga_connection = (
            db.query(GAConnection)
            .filter(GAConnection.workspace_id == workspace.id)
            .order_by(GAConnection.created_at.desc())  # Most recent first
            .first()
        )
    
    if not ga_connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No GA connection found for this workspace. Please connect Google Analytics first.",
        )
    
    # Log the query
    query_log = QueryLog(
        workspace_id=workspace.id,
        gpt_token_id=gpt_token.id,
        query_params={
            "metrics": report_request.metrics,
            "dimensions": report_request.dimensions or [],
            "date_ranges": report_request.date_ranges,
            "property_id": property_id or ga_connection.property_id,
        },
    )
    db.add(query_log)
    
    try:
        # Run the GA report
        report_data = GAService.run_report(
            connection=ga_connection,
            metrics=report_request.metrics,
            dimensions=report_request.dimensions,
            date_ranges=report_request.date_ranges,
        )
        
        # Update query log with success
        query_log.response_summary = {
            "row_count": report_data["row_count"],
            "has_totals": bool(report_data.get("totals")),
        }
        db.commit()
        
        logger.info(
            f"GA report completed successfully for workspace {workspace.id}, "
            f"returned {report_data['row_count']} rows"
        )
        
        return GAReportResponse(
            rows=report_data["rows"],
            totals=report_data.get("totals"),
            row_count=report_data["row_count"],
        )
        
    except OAuthTokenRevokedError:
        query_log.error = "GA OAuth token revoked"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="GA connection token has been revoked. Please reconnect your Google Analytics account.",
        )
        
    except GAPropertyNotFoundError as e:
        query_log.error = f"GA property not found: {str(e)}"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"GA property not found or inaccessible: {str(e)}",
        )
        
    except Exception as e:
        logger.error(
            f"Error running GA report for workspace {workspace.id}: {str(e)}",
            exc_info=True,
        )
        query_log.error = str(e)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error running GA report: {str(e)}",
        )

