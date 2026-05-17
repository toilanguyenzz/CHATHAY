"""
Shared Quiz API - Teacher creates quiz → Share link → Students take via link

This module handles:
1. Teacher creates shared quiz from document
2. Generate share code (e.g., "abc123")
3. Students access quiz via share code
4. Save quiz attempts with real Zalo names
5. Teacher dashboard: view all student results
"""

import logging
import json
import uuid
import time
from datetime import datetime, timezone
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from services.db_service import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(tags=["shared-quiz"])


# =====================================================
# 1. TEACHER: CREATE SHARED QUIZ
# =====================================================

@router.post("/api/shared-quiz/create")
async def create_shared_quiz(request: Request):
    """
    Teacher creates a shared quiz from a document.
    Returns share_code for distribution.

    Body:
    - doc_id: Document ID (optional)
    - title: Quiz title
    - subject: Subject (sinh_hoc, toan, ly, ...)
    - chapter: Chapter name
    - questions: List of questions (optional - generate from AI if not provided)
    """
    try:
        body = await request.json()
        user_id = body.get("user_id") or request.headers.get("X-User-Id", "")
        doc_id = body.get("doc_id", "")
        title = body.get("title", "Quiz")
        subject = body.get("subject", "")
        chapter = body.get("chapter", "")
        questions = body.get("questions", [])

        if not user_id:
            return JSONResponse(content={"error": "Missing user_id"}, status_code=400)

        supabase = get_supabase_client()
        if not supabase:
            return JSONResponse(content={"error": "Database not available"}, status_code=503)

        # Generate share code (8 chars)
        share_code = generate_share_code()

        # If no questions provided, generate from document
        if not questions and doc_id:
            # Get quiz questions from documents table
            doc_result = supabase.table("documents").select("quiz_questions").eq("id", doc_id).eq("user_id", user_id).execute()
            if doc_result.data and doc_result.data[0].get("quiz_questions"):
                questions = doc_result.data[0]["quiz_questions"]
                logger.info(f"✅ Loaded {len(questions)} quiz questions from document {doc_id}")
            else:
                return JSONResponse(content={"error": "Không tìm thấy câu hỏi quiz cho tài liệu này"}, status_code=400)

        if not questions:
            return JSONResponse(content={"error": "Chưa có câu hỏi quiz"}, status_code=400)

        # Insert into shared_quizzes
        result = supabase.table("shared_quizzes").insert({
            "id": str(uuid.uuid4()),
            "creator_id": user_id,
            "doc_id": doc_id or None,
            "title": title,
            "subject": subject,
            "chapter": chapter,
            "share_code": share_code,
            "questions": questions,
            "is_active": True,
            "max_attempts": body.get("max_attempts", 1),
            "expires_at": body.get("expires_at") or None,
        }).execute()

        # Return share link
        share_url = f"{request.base_url}quiz/{share_code}"

        return JSONResponse(content={
            "success": True,
            "quiz_id": result.data[0]["id"],
            "share_code": share_code,
            "share_url": share_url,
            "questions_count": len(questions),
        })

    except Exception as e:
        logger.error("Error creating shared quiz: %s", e, exc_info=True)
        return JSONResponse(content={"error": "Internal server error"}, status_code=500)


def generate_share_code() -> str:
    """Generate 8-character share code."""
    import random
    import string
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))


# =====================================================
# 2. STUDENT: ACCESS QUIZ VIA SHARE CODE
# =====================================================

@router.get("/api/shared-quiz/{share_code}")
async def get_shared_quiz(share_code: str, request: Request):
    """
    Student accesses quiz via share code.
    No login required for viewing (but required for submitting).
    """
    try:
        supabase = get_supabase_client()
        if not supabase:
            return JSONResponse(content={"error": "Database not available"}, status_code=503)

        # Get quiz from share_code
        result = supabase.table("shared_quizzes").select("*").eq("share_code", share_code).eq("is_active", True).single().execute()

        if not result.data:
            return JSONResponse(content={"error": "Quiz not found or inactive"}, status_code=404)

        quiz = result.data

        # Return quiz info (without questions for public view)
        return JSONResponse(content={
            "quiz_id": quiz["id"],
            "title": quiz["title"],
            "subject": quiz["subject"],
            "chapter": quiz["chapter"],
            "creator_id": quiz["creator_id"],
            "max_attempts": quiz["max_attempts"],
            "expires_at": quiz["expires_at"],
        })

    except Exception as e:
        logger.error("Error getting shared quiz: %s", e, exc_info=True)
        return JSONResponse(content={"error": "Internal server error"}, status_code=500)


@router.post("/api/shared-quiz/{share_code}/start")
async def start_shared_quiz(share_code: str, request: Request):
    """
    Student starts a shared quiz session.
    No login required - student provides name/phone.
    """
    try:
        body = await request.json()
        student_name = body.get("student_name", "")
        student_phone = body.get("student_phone", "")

        if not student_name or not student_phone:
            return JSONResponse(content={"error": "Cần nhập họ tên và số điện thoại"}, status_code=400)

        supabase = get_supabase_client()
        if not supabase:
            return JSONResponse(content={"error": "Database not available"}, status_code=503)

        # Get quiz
        quiz_result = supabase.table("shared_quizzes").select("*").eq("share_code", share_code).eq("is_active", True).single().execute()

        if not quiz_result.data:
            return JSONResponse(content={"error": "Quiz không tồn tại"}, status_code=404)

        quiz = quiz_result.data

        # Check attempts by phone number (student identity)
        if quiz.get("max_attempts", 1) > 0:
            attempts = supabase.table("quiz_attempts").select("*").eq("quiz_id", quiz["id"]).eq("student_phone", student_phone).execute()
            if len(attempts.data) >= quiz["max_attempts"]:
                return JSONResponse(content={"error": "Bạn đã làm quiz này rồi"}, status_code=403)

        # Return questions (for student to take quiz)
        return JSONResponse(content={
            "quiz_id": quiz["id"],
            "title": quiz["title"],
            "questions": quiz["questions"],
            "max_attempts": quiz["max_attempts"],
        })

    except Exception as e:
        logger.error("Error starting shared quiz: %s", e, exc_info=True)
        return JSONResponse(content={"error": "Internal server error"}, status_code=500)


@router.post("/api/shared-quiz/{share_code}/submit")
async def submit_shared_quiz(share_code: str, request: Request):
    """
    Student submits quiz answers.
    No login required - uses student_name and student_phone.
    Saves attempt with student info.
    """
    try:
        body = await request.json()
        student_name = body.get("student_name", "")
        student_phone = body.get("student_phone", "")
        answers = body.get("answers", [])

        if not student_name or not student_phone:
            return JSONResponse(content={"error": "Thiếu thông tin học sinh"}, status_code=400)

        if not answers:
            return JSONResponse(content={"error": "Không có câu trả lời"}, status_code=400)

        supabase = get_supabase_client()
        if not supabase:
            return JSONResponse(content={"error": "Database not available"}, status_code=503)

        # Get quiz
        quiz_result = supabase.table("shared_quizzes").select("*").eq("share_code", share_code).eq("is_active", True).single().execute()

        if not quiz_result.data:
            return JSONResponse(content={"error": "Quiz không tồn tại"}, status_code=404)

        quiz = quiz_result.data
        questions = quiz["questions"]

        # Calculate score
        score = 0
        total = len(questions)
        detailed_answers = []

        for ans in answers:
            q_idx = ans.get("question_index", 0)
            selected = ans.get("selected_option", -1)

            if 0 <= q_idx < total:
                correct = questions[q_idx].get("correct", 0)
                is_correct = selected == correct
                if is_correct:
                    score += 1

                detailed_answers.append({
                    "question_index": q_idx,
                    "question_text": questions[q_idx].get("question", ""),
                    "selected": selected,
                    "correct": correct,
                    "is_correct": is_correct,
                    "time_spent": ans.get("time_spent", 0),
                })

        percentage = (score / total * 100) if total > 0 else 0

        # Save attempt
        attempt_id = str(uuid.uuid4())
        supabase.table("quiz_attempts").insert({
            "id": attempt_id,
            "quiz_id": quiz["id"],
            "student_name": student_name,
            "student_phone": student_phone,
            "score": score,
            "total_questions": total,
            "percentage": percentage,
            "answers": detailed_answers,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }).execute()

        return JSONResponse(content={
            "success": True,
            "score": score,
            "total": total,
            "percentage": percentage,
            "attempt_id": attempt_id,
        })

    except Exception as e:
        logger.error("Error submitting shared quiz: %s", e, exc_info=True)
        return JSONResponse(content={"error": "Internal server error"}, status_code=500)


# =====================================================
# 3. TEACHER: DASHBOARD - VIEW ALL RESULTS
# =====================================================

@router.get("/api/teacher/quiz/{quiz_id}/results")
async def get_teacher_quiz_results(quiz_id: str, request: Request):
    """
    Teacher dashboard: View all student results for a quiz.
    Requires authentication (creator of quiz).
    """
    try:
        user_id = request.headers.get("X-User-Id", "")

        if not user_id:
            return JSONResponse(content={"error": "Authentication required"}, status_code=401)

        supabase = get_supabase_client()
        if not supabase:
            return JSONResponse(content={"error": "Database not available"}, status_code=503)

        # Verify teacher is creator
        quiz = supabase.table("shared_quizzes").select("creator_id, title").eq("id", quiz_id).single().execute()

        if not quiz.data or quiz.data["creator_id"] != user_id:
            return JSONResponse(content={"error": "Unauthorized"}, status_code=403)

        # Get all attempts
        attempts = supabase.table("quiz_attempts").select("*").eq("quiz_id", quiz_id).order("score", desc=True).execute()

        # Calculate statistics
        results = attempts.data or []
        total_students = len(results)
        avg_score = sum(r["score"] for r in results) / total_students if total_students > 0 else 0
        avg_percentage = sum(r["percentage"] for r in results) / total_students if total_students > 0 else 0

        # Get quiz details
        quiz_detail = supabase.table("shared_quizzes").select("*").eq("id", quiz_id).single().execute()

        return JSONResponse(content={
            "quiz_id": quiz_id,
            "title": quiz.data["title"],
            "total_questions": len(quiz_detail.data.get("questions", [])),
            "total_students": total_students,
            "average_score": round(avg_score, 2),
            "average_percentage": round(avg_percentage, 2),
            "results": [
                {
                    "student_name": r.get("student_name", r.get("display_name", "")),
                    "student_phone": r.get("student_phone", ""),
                    "score": r["score"],
                    "total": r["total_questions"],
                    "percentage": r["percentage"],
                    "completed_at": r["completed_at"],
                }
                for r in results
            ],
        })

    except Exception as e:
        logger.error("Error getting teacher quiz results: %s", e, exc_info=True)
        return JSONResponse(content={"error": "Internal server error"}, status_code=500)


# =====================================================
# 4. USER PROFILE: CREATE/UPDATE FROM ZALO
# =====================================================

@router.post("/api/user-profile")
async def create_or_update_user_profile(request: Request):
    """
    Create or update user profile with real Zalo info.
    Called after Zalo authentication.
    """
    try:
        body = await request.json()
        user_id = body.get("user_id", "")
        display_name = body.get("display_name", "")
        avatar_url = body.get("avatar_url", "")
        role = body.get("role", "student")  # 'student' or 'teacher'

        if not user_id or not display_name:
            return JSONResponse(content={"error": "user_id and display_name required"}, status_code=400)

        supabase = get_supabase_client()
        if not supabase:
            return JSONResponse(content={"error": "Database not available"}, status_code=503)

        # Upsert user profile
        supabase.table("user_profiles").upsert({
            "user_id": user_id,
            "display_name": display_name,
            "avatar_url": avatar_url,
            "role": role,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).execute()

        return JSONResponse(content={
            "success": True,
            "user_id": user_id,
            "display_name": display_name,
        })

    except Exception as e:
        logger.error("Error creating user profile: %s", e, exc_info=True)
        return JSONResponse(content={"error": "Internal server error"}, status_code=500)


@router.get("/api/user-profile/{user_id}")
async def get_user_profile(user_id: str):
    """Get user profile by user_id."""
    try:
        supabase = get_supabase_client()
        if not supabase:
            return JSONResponse(content={"error": "Database not available"}, status_code=503)

        result = supabase.table("user_profiles").select("*").eq("user_id", user_id).execute()

        if not result.data or len(result.data) == 0:
            return JSONResponse(content={"error": "User not found"}, status_code=404)

        return JSONResponse(content=result.data[0])

    except Exception as e:
        logger.error("Error getting user profile: %s", e, exc_info=True)
        return JSONResponse(content={"error": "Internal server error"}, status_code=500)