from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, status

from services.prompt_manager import prompt_manager
from services.logging_config import get_logger
from schemas.admin import (
    PromptUpdateRequest,
    PromptTestRequest,
    RestorePromptRequest,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/prompt")


@router.get("")
async def get_all_prompts():
    """Get all prompts with metadata."""

    try:
        prompts = prompt_manager.get_all_prompts()

        # Group prompts by category for better organization
        grouped_prompts = {}
        for prompt_name, prompt_data in prompts.items():
            category = prompt_data['category']
            if category not in grouped_prompts:
                grouped_prompts[category] = []

            grouped_prompts[category].append({
                'name': prompt_name,
                'description': prompt_data['description'],
                'variables': prompt_data['variables'],
                'content_length': len(prompt_data['content'])
            })

        return {
            'total_prompts': len(prompts),
            'categories': grouped_prompts,
            'prompts': prompts
        }

    except Exception as e:
        logger.error(f"Error getting prompts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving prompts: {str(e)}"
        )


@router.get("/{prompt_name}")
async def get_prompt(
    prompt_name: str
):
    """Get a specific prompt by name."""

    try:
        prompt = prompt_manager.get_prompt(prompt_name)

        if not prompt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prompt '{prompt_name}' not found"
            )

        return prompt

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting prompt {prompt_name}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving prompt: {str(e)}"
        )


@router.put("/{prompt_name}")
async def update_prompt(
    request: Request,
    body: PromptUpdateRequest,
    prompt_name: str,
):
    """Update a specific prompt."""

    admin_id = str(request.state.user_id)

    try:
        success = prompt_manager.update_prompt(prompt_name, body.content, admin_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to update prompt '{prompt_name}'"
            )

        # Get updated prompt to return
        updated_prompt = prompt_manager.get_prompt(prompt_name)

        logger.info(f"Admin {admin_id} updated prompt {prompt_name}")

        return {
            'success': True,
            'message': f"Prompt '{prompt_name}' updated successfully",
            'prompt': updated_prompt
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating prompt {prompt_name}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating prompt: {str(e)}"
        )


@router.get("/{prompt_name}/history")
async def get_prompt_history(
    prompt_name: str
):
    """Get version history for a specific prompt."""

    try:
        history = prompt_manager.get_prompt_history(prompt_name)

        return {
            'prompt_name': prompt_name,
            'total_versions': len(history),
            'history': history
        }

    except Exception as e:
        logger.error(f"Error getting history for prompt {prompt_name}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving prompt history: {str(e)}"
        )


@router.post("/{prompt_name}/test")
async def test_prompt(
    body: PromptTestRequest,
    prompt_name: str,
):
    """Test a prompt with provided variables."""

    try:
        result = prompt_manager.test_prompt(prompt_name, body.variables)

        return {
            'prompt_name': prompt_name,
            'test_result': result
        }

    except Exception as e:
        logger.error(f"Error testing prompt {prompt_name}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error testing prompt: {str(e)}"
        )


@router.get("/status")
async def get_admin_status():
    """Get admin interface status."""

    try:
        # Get some basic stats
        prompts = prompt_manager.get_all_prompts()

        # Count backups
        backup_count = 0
        try:
            backup_dir = prompt_manager.backup_dir
            if backup_dir.exists():
                backup_count = len(list(backup_dir.glob("*.json")))
        except:
            pass

        return {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'prompts_loaded': len(prompts),
            'backup_files': backup_count,
            'categories': list(set([p['category'] for p in prompts.values()]))
        }

    except Exception as e:
        logger.error(f"Error getting admin status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting admin status: {str(e)}"
        )


# Status endpoint
@router.post("/{prompt_name}/restore")
async def restore_prompt(
    request: Request,
    body: RestorePromptRequest,
    prompt_name: str,
):
    """Restore a prompt from a backup."""

    admin_id = str(request.state.user_id)

    try:
        success = prompt_manager.restore_prompt(prompt_name, body.backup_filename, admin_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to restore prompt '{prompt_name}' from backup '{body.backup_filename}'"
            )

        # Get restored prompt to return
        restored_prompt = prompt_manager.get_prompt(prompt_name)

        logger.info(f"Admin {admin_id} restored prompt {prompt_name} from {body.backup_filename}")

        return {
            'success': True,
            'message': f"Prompt '{prompt_name}' restored successfully from '{body.backup_filename}'",
            'prompt': restored_prompt
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restoring prompt {prompt_name}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error restoring prompt: {str(e)}"
        )
