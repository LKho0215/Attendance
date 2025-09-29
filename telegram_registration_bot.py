"""
Telegram Bot Self-Registration System
Allows employees to register themselves for face recognition attendance system
"""

import asyncio
import os
import logging
import cv2
import numpy as np
from datetime import datetime
from typing import Dict, Any, Optional
import json
import base64
from io import BytesIO
from PIL import Image

# Telegram bot imports
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# Import our existing modules
import sys
sys.path.append(os.path.dirname(__file__))
from core.database import DatabaseManager
from core.deepface_recognition import DeepFaceRecognitionSystem
from core.mongodb_manager import MongoDBManager

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramRegistrationBot:
    def __init__(self, token: str, use_mongodb: bool = False):
        """Initialize the Telegram registration bot"""
        self.token = token
        self.use_mongodb = use_mongodb
        
        # Initialize database
        if use_mongodb:
            self.db = MongoDBManager()
        else:
            self.db = DatabaseManager()
        
        # Initialize face recognition
        self.face_recognition = DeepFaceRecognitionSystem()
        
        # Store registration sessions
        self.registration_sessions: Dict[int, Dict[str, Any]] = {}
        
        # Admin user IDs (configure these)
        self.admin_ids = set()  # Add admin Telegram user IDs here
        
        logger.info("Telegram Registration Bot initialized")
    
    def add_admin(self, user_id: int):
        """Add an admin user ID"""
        self.admin_ids.add(user_id)
        logger.info(f"Added admin user ID: {user_id}")
    
    def check_employee_exists(self, employee_id: str):
        """Check if an employee already exists in the database"""
        try:
            if hasattr(self.db, 'get_employee'):
                # MongoDB or Database with get_employee method
                return self.db.get_employee(employee_id)
            else:
                # Fallback for other database types
                logger.warning("Database doesn't have get_employee method")
                return None
        except Exception as e:
            logger.error(f"Error checking if employee exists: {e}")
            return None
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        user_id = user.id
        
        welcome_text = f"""
🏢 **Employee Self-Registration System**

Hello {user.first_name}! 👋

This bot allows you to register for the face recognition attendance system.

**📋 Registration Process:**
1️⃣ Provide your Employee ID
2️⃣ Enter your full name
3️⃣ Select your role (Staff/Security)
4️⃣ Upload a clear photo of your face
5️⃣ Wait for admin approval

**📸 Photo Guidelines:**
- Good lighting, face clearly visible
- Look directly at camera
- No sunglasses or masks
- High quality image preferred

Ready to start? Use /register to begin!

**Commands:**
/register - Start registration process
/status - Check registration status
/help - Show this help message
"""
        
        await update.message.reply_text(
            welcome_text, 
            parse_mode='Markdown',
            reply_markup=self.get_main_menu_keyboard()
        )
    
    def get_main_menu_keyboard(self):
        """Get the main menu keyboard"""
        keyboard = [
            [KeyboardButton("🆔 Register New Employee")],
            [KeyboardButton("📊 Check Status"), KeyboardButton("❓ Help")],
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    
    async def register_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /register command"""
        user_id = update.effective_user.id
        
        # Check if user already has a pending registration
        if user_id in self.registration_sessions:
            session = self.registration_sessions[user_id]
            if session.get('status') == 'pending_approval':
                await update.message.reply_text(
                    "⏳ You already have a registration pending approval.\n"
                    "Please wait for admin review."
                )
                return
            elif session.get('status') == 'approved':
                await update.message.reply_text(
                    "✅ You are already registered and approved!\n"
                    "Your face recognition is active."
                )
                return
        
        # Start new registration session
        self.registration_sessions[user_id] = {
            'status': 'collecting_employee_id',
            'user_info': {
                'telegram_user_id': user_id,
                'telegram_username': update.effective_user.username,
                'telegram_first_name': update.effective_user.first_name,
                'telegram_last_name': update.effective_user.last_name,
                'registration_start': datetime.now().isoformat()
            }
        }
        
        await update.message.reply_text(
            "🆔 **Step 1/4: Employee ID**\n\n"
            "Please enter your Employee ID:\n"
            "• Must be 3-10 characters\n"
            "• Can contain letters and numbers\n"
            "• Example: EMP001, STAFF123, SEC456\n\n"
            "Type your Employee ID:",
            parse_mode='Markdown'
        )
    
    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages during registration"""
        user_id = update.effective_user.id
        text = update.message.text.strip()
        
        # Handle menu buttons
        if text == "🆔 Register New Employee":
            await self.register_command(update, context)
            return
        elif text == "📊 Check Status":
            await self.status_command(update, context)
            return
        elif text == "❓ Help":
            await self.start_command(update, context)
            return
        
        # Check if user has an active registration session
        if user_id not in self.registration_sessions:
            await update.message.reply_text(
                "❌ No active registration session.\n"
                "Use /register or click 'Register New Employee' to start."
            )
            return
        
        session = self.registration_sessions[user_id]
        status = session['status']
        
        if status == 'collecting_employee_id':
            await self.process_employee_id(update, context, text)
        elif status == 'collecting_name':
            await self.process_name(update, context, text)
        elif status == 'collecting_department':
            await self.process_department(update, context, text)
        else:
            await update.message.reply_text(
                "⚠️ Unexpected input. Please follow the registration steps."
            )
    
    async def process_employee_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE, employee_id: str):
        """Process employee ID input"""
        user_id = update.effective_user.id
        
        # Validate employee ID format
        if not self.validate_employee_id(employee_id):
            await update.message.reply_text(
                "❌ Invalid Employee ID format!\n\n"
                "Requirements:\n"
                "• 3-10 characters long\n"
                "• Letters and numbers only\n"
                "• No spaces or special characters\n\n"
                "Please try again:"
            )
            return
        
        # Check if employee ID already exists
        existing_employee = self.check_employee_exists(employee_id)
        
        if existing_employee:
            # Employee exists - offer re-registration
            self.registration_sessions[user_id]['employee_id'] = employee_id.upper()
            self.registration_sessions[user_id]['existing_employee'] = existing_employee
            self.registration_sessions[user_id]['is_update'] = True
            self.registration_sessions[user_id]['status'] = 'confirming_update'
            
            # Create confirmation keyboard
            keyboard = [
                [InlineKeyboardButton("🔄 Yes, Update Face Data", callback_data="confirm_update")],
                [InlineKeyboardButton("❌ No, Enter Different ID", callback_data="cancel_update")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"👤 **Employee Found!**\n\n"
                f"🆔 ID: {employee_id.upper()}\n"
                f"👤 Name: {existing_employee.get('name', 'N/A')}\n"
                f"🎭 Role: {existing_employee.get('role', 'N/A')}\n"
                f"📅 Registered: {existing_employee.get('created_at', 'N/A')}\n\n"
                f"⚠️ **This employee is already registered.**\n\n"
                f"🔄 **Update Options:**\n"
                f"• Update face recognition data with new photos\n"
                f"• Keep existing name and role information\n"
                f"• Improve recognition accuracy\n\n"
                f"Do you want to update the face recognition data?",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        else:
            # New employee - continue with normal registration
            self.registration_sessions[user_id]['employee_id'] = employee_id.upper()
            self.registration_sessions[user_id]['is_update'] = False
            self.registration_sessions[user_id]['status'] = 'collecting_name'
            
            await update.message.reply_text(
                f"✅ Employee ID: {employee_id.upper()}\n\n"
                "👤 **Step 2/5: Full Name**\n\n"
                "Please enter your full name:\n"
                "• First and last name\n"
                "• Example: John Smith, Mary Johnson\n\n"
                "Type your full name:",
                parse_mode='Markdown'
            )
    
    async def process_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE, name: str):
        """Process name input"""
        user_id = update.effective_user.id
        
        # Validate name
        if not self.validate_name(name):
            await update.message.reply_text(
                "❌ Invalid name format!\n\n"
                "Requirements:\n"
                "• 2-50 characters\n"
                "• Letters and spaces only\n"
                "• At least first and last name\n\n"
                "Please try again:"
            )
            return
        
        # Save name and move to department collection
        self.registration_sessions[user_id]['name'] = name.title()
        self.registration_sessions[user_id]['status'] = 'collecting_department'
        
        await update.message.reply_text(
            f"✅ Name: {name.title()}\n\n"
            "🏢 **Step 3/5: Department**\n\n"
            "Please enter your department:\n"
            "• Examples: Engineering, HR, Finance, Marketing\n"
            "• Sales, Operations, Security, Administration\n"
            "• IT, Customer Service, Quality Assurance\n\n"
            "Type your department:",
            parse_mode='Markdown'
        )
    
    async def process_department(self, update: Update, context: ContextTypes.DEFAULT_TYPE, department: str):
        """Process department input"""
        user_id = update.effective_user.id
        
        # Validate department
        if not self.validate_department(department):
            await update.message.reply_text(
                "❌ Invalid department format!\n\n"
                "Requirements:\n"
                "• 2-30 characters\n"
                "• Letters and spaces only\n"
                "• Examples: Engineering, HR, Finance\n\n"
                "Please try again:"
            )
            return
        
        # Save department and move to role selection
        self.registration_sessions[user_id]['department'] = department.title()
        self.registration_sessions[user_id]['status'] = 'selecting_role'
        
        # Create role selection keyboard
        keyboard = [
            [InlineKeyboardButton("👥 Staff", callback_data="role_staff")],
            [InlineKeyboardButton("🛡️ Security", callback_data="role_security")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ Department: {department.title()}\n\n"
            "🎭 **Step 4/5: Role Selection**\n\n"
            "Please select your role:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button callbacks"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        data = query.data
        
        if user_id not in self.registration_sessions:
            await query.edit_message_text("❌ Registration session expired. Please start again with /register")
            return
        
        session = self.registration_sessions[user_id]
        
        if data == "confirm_update":
            # User wants to update existing employee
            session['status'] = 'collecting_photo'
            
            await query.edit_message_text(
                f"🔄 **Updating Face Recognition Data**\n\n"
                f"🆔 Employee: {session['existing_employee']['name']}\n"
                f"🆔 ID: {session['employee_id']}\n\n"
                f"📸 **Step: Enhanced Face Photo Capture**\n\n"
                f"**Multi-Angle Capture Process:**\n"
                f"• You'll be guided through 8 different poses\n"
                f"• Look straight, turn left/right, tilt up/down\n"
                f"• Different expressions (neutral, smile, serious)\n"
                f"• This creates robust face recognition\n\n"
                f"**Photo Requirements:**\n"
                f"• Clear, well-lit photo of your face\n"
                f"• Look directly at the camera\n"
                f"• No sunglasses, masks, or hats\n"
                f"• Follow the guided instructions\n\n"
                f"📱 **Ready to start multi-angle capture?**\n"
                f"Send your first photo when ready!",
                parse_mode='Markdown'
            )
            
        elif data == "cancel_update":
            # User wants to enter different ID
            session['status'] = 'collecting_employee_id'
            if 'existing_employee' in session:
                del session['existing_employee']
            if 'is_update' in session:
                del session['is_update']
            
            await query.edit_message_text(
                "🆔 **Step 1/4: Employee ID**\n\n"
                "Please enter your Employee ID:\n"
                "• Must be 3-10 characters\n"
                "• Can contain letters and numbers\n"
                "• Example: EMP001, STAFF123, SEC456\n\n"
                "Type your Employee ID:",
                parse_mode='Markdown'
            )
        
        elif data.startswith("role_"):
            role = data.split("_")[1]
            session['role'] = role.capitalize()
            session['status'] = 'collecting_photo'
            
            role_emoji = "🛡️" if role == "security" else "👥"
            
            await query.edit_message_text(
                f"✅ Role: {role_emoji} {role.capitalize()}\n\n"
                f"📸 **Step 5/5: Multi-Angle Face Capture**\n\n"
                f"**Enhanced Capture Process:**\n"
                f"• You'll be guided through 8 different poses\n"
                f"• Look straight, turn left/right, tilt up/down\n"
                f"• Different expressions (neutral, smile, serious)\n"
                f"• This creates robust face recognition\n\n"
                f"**Photo Requirements:**\n"
                f"• Clear, well-lit photo of your face\n"
                f"• Look directly at the camera\n"
                f"• No sunglasses, masks, or hats\n"
                f"• Follow the guided instructions\n\n"
                f"**Ready to start multi-angle capture?**\n"
                f"Send your first photo when ready!",
                parse_mode='Markdown'
            )
        
        elif data.startswith("admin_"):
            await self.handle_admin_callback(query, context)
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo upload with multi-angle capture"""
        user_id = update.effective_user.id
        
        if user_id not in self.registration_sessions:
            await update.message.reply_text(
                "❌ No active registration session. Use /register to start."
            )
            return
        
        session = self.registration_sessions[user_id]
        if session['status'] != 'collecting_photo':
            await update.message.reply_text(
                "⚠️ Please complete the previous steps first."
            )
            return
        
        # Initialize multi-angle capture if not started
        if 'capture_state' not in session:
            session['capture_state'] = {
                'current_step': 0,
                'captured_vectors': [],
                'instructions': [
                    "Look straight at the camera with a NEUTRAL expression",
                    "Turn your head slightly to the LEFT (keep looking at camera)",
                    "Turn your head slightly to the RIGHT (keep looking at camera)",
                    "Look straight and SMILE naturally",
                    "Look straight with a SERIOUS expression",
                    "Tilt your head slightly UP (chin up a bit)",
                    "Tilt your head slightly DOWN (chin down a bit)",
                    "Look straight again - FINAL CAPTURE"
                ]
            }
            
            # Send initial instruction
            current_instruction = session['capture_state']['instructions'][0]
            await update.message.reply_text(
                f"📸 **Multi-Angle Face Capture Started!**\n\n"
                f"**Step 1/8:** {current_instruction}\n\n"
                f"📱 Take a photo following this instruction and send it.\n"
                f"Each pose helps create more accurate recognition!",
                parse_mode='Markdown'
            )
            return
        
        # Process current photo
        try:
            capture_state = session['capture_state']
            current_step = capture_state['current_step']
            current_instruction = capture_state['instructions'][current_step]
            
            # Get the largest photo size
            photo = update.message.photo[-1]
            
            # Download photo
            file = await context.bot.get_file(photo.file_id)
            photo_bytes = await file.download_as_bytearray()
            
            # Convert to OpenCV format
            image = Image.open(BytesIO(photo_bytes))
            image_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Process face and extract vector
            processing_msg = await update.message.reply_text(
                f"🔄 **Processing Step {current_step + 1}/8...**\n"
                f"📋 Pose: {current_instruction}\n"
                f"• Detecting face\n"
                f"• Extracting features\n"
                f"• Validating quality"
            )
            
            face_vector = await self.process_single_pose(image_cv, current_instruction)
            
            if face_vector is None:
                await processing_msg.edit_text(
                    f"❌ **Step {current_step + 1}/8 Failed**\n\n"
                    f"📋 Pose: {current_instruction}\n\n"
                    f"**Issues:**\n"
                    f"• Face not clearly visible or too small\n"
                    f"• Poor lighting conditions\n"
                    f"• Multiple faces in the photo\n"
                    f"• Face partially covered\n\n"
                    f"**💡 Tips:**\n"
                    f"• Use good lighting\n"
                    f"• Face should fill 30-50% of frame\n"
                    f"• Follow the pose instruction exactly\n\n"
                    f"📸 **Please retry this pose:**\n"
                    f"Take another photo following: *{current_instruction}*",
                    parse_mode='Markdown'
                )
                return
            
            # Save successful capture
            capture_state['captured_vectors'].append({
                'vector': face_vector,
                'instruction': current_instruction,
                'step': current_step + 1
            })
            
            await processing_msg.edit_text(
                f"✅ **Step {current_step + 1}/8 Successful!**\n\n"
                f"📋 Pose: {current_instruction}\n"
                f" Face vector captured successfully!\n\n"
                f" Progress: {len(capture_state['captured_vectors'])}/8 poses completed",
                parse_mode='Markdown'
            )
            
            # Move to next step
            capture_state['current_step'] += 1
            
            # Check if all poses completed
            if capture_state['current_step'] >= len(capture_state['instructions']):
                await self.complete_multi_angle_capture(update, context, session)
            else:
                # Send next instruction
                next_instruction = capture_state['instructions'][capture_state['current_step']]
                await update.message.reply_text(
                    f"📸 **Next Pose Ready!**\n\n"
                    f"**Step {capture_state['current_step'] + 1}/8:** {next_instruction}\n\n"
                    f"📱 Take a photo following this instruction.\n\n"
                    f"📊 Progress: {len(capture_state['captured_vectors'])}/8 completed",
                    parse_mode='Markdown'
                )
            
        except Exception as e:
            logger.error(f"Error processing photo: {e}")
            await update.message.reply_text(
                f"❌ Error processing photo: {str(e)}\n\n"
                f"Please try again or contact support."
            )
    
    async def process_face_photo(self, image_cv: np.ndarray, session: dict) -> Optional[list]:
        """Process face photo and extract vector with improved detection"""
        try:
            logger.info(f"Processing face photo for {session.get('employee_id', 'unknown')} - Image shape: {image_cv.shape}")
            
            # Method 1: Try fast face detection first
            faces = self.face_recognition.detect_faces_fast(image_cv)
            logger.info(f"Fast detection found {len(faces)} faces")
            
            # Method 2: If fast detection fails, try direct embedding extraction
            if len(faces) == 0:
                logger.info("No faces with fast detection, trying direct embedding extraction...")
                face_embedding, face_region = self.face_recognition.extract_face_embedding_hybrid(image_cv)
                
                if face_embedding is not None:
                    logger.info("Successfully extracted embedding with hybrid method")
                    return face_embedding.tolist()
                
                # Method 3: Try DeepFace-only method as fallback
                logger.info("Hybrid method failed, trying DeepFace-only method...")
                face_embedding, face_region = self.face_recognition.extract_face_embedding_deepface_only(image_cv)
                
                if face_embedding is not None:
                    logger.info("Successfully extracted embedding with DeepFace-only method")
                    return face_embedding.tolist()
                
                logger.warning("All face detection methods failed - no face detected")
                return None
            
            elif len(faces) > 1:
                logger.warning(f"Multiple faces detected ({len(faces)}), will process the largest one")
                # Sort faces by size and take the largest
                faces_with_size = [(face, (face[2] - face[0]) * (face[3] - face[1])) for face in faces]
                faces_with_size.sort(key=lambda x: x[1], reverse=True)
                largest_face = faces_with_size[0][0]
                logger.info(f"Selected largest face: {largest_face}")
            
            # Extract face embedding using the hybrid method
            face_embedding, face_region = self.face_recognition.extract_face_embedding_hybrid(image_cv)
            
            if face_embedding is None:
                # Fallback to DeepFace-only method
                logger.info("Hybrid method failed, trying DeepFace-only fallback...")
                face_embedding, face_region = self.face_recognition.extract_face_embedding_deepface_only(image_cv)
            
            if face_embedding is None:
                logger.warning("Failed to extract face embedding with all methods")
                return None
            
            logger.info(f"Successfully extracted face vector for {session.get('employee_id', 'unknown')} - Vector size: {len(face_embedding)}")
            return face_embedding.tolist()  # Convert to list for JSON serialization
            
        except Exception as e:
            logger.error(f"Error processing face photo: {e}", exc_info=True)
            return None
    
    async def process_single_pose(self, image_cv: np.ndarray, instruction: str) -> Optional[list]:
        """Process a single pose and extract face vector"""
        try:
            logger.info(f"Processing pose: {instruction} - Image shape: {image_cv.shape}")
            
            # Use the same robust detection as the main process_face_photo
            faces = self.face_recognition.detect_faces_fast(image_cv)
            logger.info(f"Fast detection found {len(faces)} faces for pose: {instruction}")
            
            if len(faces) == 0:
                logger.info(f"No faces with fast detection for pose {instruction}, trying direct embedding extraction...")
                face_embedding, face_region = self.face_recognition.extract_face_embedding_hybrid(image_cv)
                
                if face_embedding is not None:
                    logger.info(f"Successfully extracted embedding with hybrid method for pose: {instruction}")
                    return face_embedding.tolist()
                
                # Try DeepFace-only method as fallback
                logger.info(f"Hybrid method failed for pose {instruction}, trying DeepFace-only method...")
                face_embedding, face_region = self.face_recognition.extract_face_embedding_deepface_only(image_cv)
                
                if face_embedding is not None:
                    logger.info(f"Successfully extracted embedding with DeepFace-only method for pose: {instruction}")
                    return face_embedding.tolist()
                
                logger.warning(f"All face detection methods failed for pose: {instruction}")
                return None
            
            elif len(faces) > 1:
                logger.warning(f"Multiple faces detected ({len(faces)}) for pose {instruction}, will process the largest one")
                # Sort faces by size and take the largest
                faces_with_size = [(face, (face[2] - face[0]) * (face[3] - face[1])) for face in faces]
                faces_with_size.sort(key=lambda x: x[1], reverse=True)
                largest_face = faces_with_size[0][0]
                logger.info(f"Selected largest face for pose {instruction}: {largest_face}")
            
            # Extract face embedding using the hybrid method
            face_embedding, face_region = self.face_recognition.extract_face_embedding_hybrid(image_cv)
            
            if face_embedding is None:
                # Fallback to DeepFace-only method
                logger.info(f"Hybrid method failed for pose {instruction}, trying DeepFace-only fallback...")
                face_embedding, face_region = self.face_recognition.extract_face_embedding_deepface_only(image_cv)
            
            if face_embedding is None:
                logger.warning(f"Failed to extract face embedding for pose {instruction} with all methods")
                return None
            
            logger.info(f"Successfully extracted face vector for pose {instruction} - Vector size: {len(face_embedding)}")
            return face_embedding.tolist()
                
        except Exception as e:
            logger.error(f"Error processing pose '{instruction}': {e}", exc_info=True)
            return None

    async def complete_multi_angle_capture(self, update: Update, context: ContextTypes.DEFAULT_TYPE, session: dict):
        """Complete multi-angle capture process"""
        try:
            capture_state = session['capture_state']
            captured_vectors = capture_state['captured_vectors']
            
            if len(captured_vectors) < 3:
                await update.message.reply_text(
                    "❌ **Insufficient face captures!**\n\n"
                    f"Only {len(captured_vectors)}/8 poses completed.\n"
                    "Please restart registration with /register to ensure accurate recognition.",
                    parse_mode='Markdown'
                )
                del self.registration_sessions[update.effective_user.id]
                return
            
            # Calculate average face vector from all captures
            all_vectors = [capture['vector'] for capture in captured_vectors]
            averaged_vector = np.mean(all_vectors, axis=0)
            
            # Save final data
            session['face_vector'] = averaged_vector.tolist()
            session['capture_count'] = len(captured_vectors)
            session['capture_details'] = [
                {
                    'instruction': capture['instruction'],
                    'step': capture['step']
                } for capture in captured_vectors
            ]
            session['status'] = 'pending_approval'
            session['submitted_at'] = datetime.now().isoformat()
            
            # Clean up capture state
            del session['capture_state']
            
            # Final success message
            await update.message.reply_text(
                "🎉 **Multi-Angle Registration Complete!**\n\n"
                "📋 **Your Information:**\n"
                f"🆔 Employee ID: {session['employee_id']}\n"
                f"👤 Name: {session['name']}\n"
                f"� Department: {session['department']}\n"
                f"�🎭 Role: {session['role']}\n"
                f"📸 Face Captures: {len(captured_vectors)}/8 poses\n\n"
                "✅ **Advanced Face Recognition Setup:**\n"
                f"• Multiple angles captured for better accuracy\n"
                f"• Face vectors averaged for robust recognition\n"
                f"• Quality validated across all poses\n\n"
                "⏳ **Status:** Pending Admin Approval\n\n"
                "Your registration has been submitted for review. "
                "You'll be notified once it's approved!",
                parse_mode='Markdown'
            )
            
            # Notify admins
            await self.notify_admins_new_registration(session, context)
            
        except Exception as e:
            logger.error(f"Error completing multi-angle capture: {e}", exc_info=True)
            await update.message.reply_text(
                "❌ Error completing registration. Please try again or contact support."
            )
    
    async def notify_admins_new_registration(self, session: dict, context: ContextTypes.DEFAULT_TYPE):
        """Notify admins of new registration"""
        if not self.admin_ids:
            logger.warning("No admin IDs configured")
            return
        
        user_info = session['user_info']
        
        # Check if this was multi-angle capture
        capture_info = ""
        if 'capture_count' in session:
            capture_info = f"\n📸 **Multi-Angle Capture:** {session['capture_count']}/8 poses completed"
            capture_info += f"\n🎯 **Advanced Recognition:** Face vectors averaged for accuracy"
        
        admin_message = f"""
🔔 **New Registration Request**

🆔 **Employee ID:** {session['employee_id']}
👤 **Name:** {session['name']}
� **Department:** {session['department']}
�🎭 **Role:** {session['role']}
📱 **Telegram:** @{user_info.get('telegram_username', 'N/A')}
⏰ **Submitted:** {session['submitted_at']}{capture_info}

📸 **Photo Status:** Ready for review
🤖 **Face Vector:** Extracted ✓
"""
        
        # Create admin action buttons
        keyboard = [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"admin_approve_{session['user_info']['telegram_user_id']}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"admin_reject_{session['user_info']['telegram_user_id']}")
            ],
            [InlineKeyboardButton("👁️ View Details", callback_data=f"admin_details_{session['user_info']['telegram_user_id']}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        for admin_id in self.admin_ids:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=admin_message,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
                
                # Send the photo to admin for review
                photo_bytes = base64.b64decode(session['photo_data'])
                await context.bot.send_photo(
                    chat_id=admin_id,
                    photo=BytesIO(photo_bytes),
                    caption=f"📸 Registration Photo for {session['employee_id']} - {session['name']}"
                )
                
            except Exception as e:
                logger.error(f"Error notifying admin {admin_id}: {e}")
    
    async def handle_admin_callback(self, query, context):
        """Handle admin approval/rejection callbacks"""
        user_id = query.from_user.id
        
        if user_id not in self.admin_ids:
            await query.answer("❌ Unauthorized", show_alert=True)
            return
        
        action, target_user_id = query.data.split("_", 2)[1:]
        target_user_id = int(target_user_id)
        
        if target_user_id not in self.registration_sessions:
            await query.edit_message_text("❌ Registration session not found")
            return
        
        session = self.registration_sessions[target_user_id]
        
        if action == "approve":
            await self.approve_registration(session, query, context)
        elif action == "reject":
            await self.reject_registration(session, query, context)
        elif action == "details":
            await self.show_registration_details(session, query, context)
    
    async def approve_registration(self, session: dict, query, context):
        """Approve a registration"""
        try:
            # Add employee to database
            employee_data = {
                'employee_id': session['employee_id'],
                'name': session['name'],
                'department': session['department'],
                'role': session['role'],
                'telegram_user_id': session['user_info']['telegram_user_id'],
                'registered_via': 'telegram_bot',
                'approved_by': query.from_user.id,
                'approved_at': datetime.now().isoformat()
            }
            
            # Convert face vector back to numpy array
            face_vector = np.array(session['face_vector'])
            
            # Add to database with face vector
            if self.use_mongodb:
                success = self.db.add_employee_with_face_vector(
                    employee_data['employee_id'],
                    employee_data['name'],
                    face_vector,
                    department=employee_data['department'],
                    role=employee_data['role']
                )
            else:
                success = self.db.add_employee_with_face_vector(
                    employee_data['employee_id'],
                    employee_data['name'],
                    face_vector,
                    department=employee_data['department'],
                    role=employee_data['role']
                )
            
            if success:
                session['status'] = 'approved'
                session['approved_at'] = datetime.now().isoformat()
                
                # Notify user of approval
                await context.bot.send_message(
                    chat_id=session['user_info']['telegram_user_id'],
                    text=f"🎉 **Registration Approved!**\n\n"
                         f"✅ Your registration has been approved by admin.\n"
                         f"🆔 Employee ID: {session['employee_id']}\n"
                         f"👤 Name: {session['name']}\n"
                         f"🎭 Role: {session['role']}\n\n"
                         f"🚀 You can now use face recognition at the attendance kiosk!",
                    parse_mode='Markdown'
                )
                
                await query.edit_message_text(
                    f"✅ **Registration Approved**\n\n"
                    f"Employee {session['employee_id']} - {session['name']} has been approved and added to the system."
                )
                
                logger.info(f"Registration approved for {session['employee_id']} - {session['name']}")
                
            else:
                await query.edit_message_text(
                    "❌ **Database Error**\n\nFailed to add employee to database. Please try again."
                )
                
        except Exception as e:
            logger.error(f"Error approving registration: {e}")
            await query.edit_message_text(
                f"❌ **Error:** {str(e)}"
            )
    
    async def reject_registration(self, session: dict, query, context):
        """Reject a registration"""
        session['status'] = 'rejected'
        session['rejected_at'] = datetime.now().isoformat()
        session['rejected_by'] = query.from_user.id
        
        # Notify user of rejection
        await context.bot.send_message(
            chat_id=session['user_info']['telegram_user_id'],
            text=f"❌ **Registration Rejected**\n\n"
                 f"Your registration has been rejected by admin.\n\n"
                 f"🔄 You can start a new registration with /register\n"
                 f"📞 Contact admin if you have questions.",
            parse_mode='Markdown'
        )
        
        await query.edit_message_text(
            f"❌ **Registration Rejected**\n\n"
            f"Employee {session['employee_id']} - {session['name']} registration has been rejected."
        )
        
        logger.info(f"Registration rejected for {session['employee_id']} - {session['name']}")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        user_id = update.effective_user.id
        
        if user_id not in self.registration_sessions:
            await update.message.reply_text(
                "❌ No registration found.\n"
                "Use /register to start the registration process."
            )
            return
        
        session = self.registration_sessions[user_id]
        status = session['status']
        
        status_messages = {
            'collecting_employee_id': "⏳ Waiting for Employee ID",
            'collecting_name': "⏳ Waiting for Full Name",
            'selecting_role': "⏳ Waiting for Role Selection",
            'collecting_photo': "⏳ Waiting for Photo Upload",
            'pending_approval': "⏳ Pending Admin Approval",
            'approved': "✅ Approved - Registration Complete",
            'rejected': "❌ Rejected - Please start new registration"
        }
        
        status_text = f"""
📊 **Registration Status**

🆔 Employee ID: {session.get('employee_id', 'Not provided')}
👤 Name: {session.get('name', 'Not provided')}
🎭 Role: {session.get('role', 'Not selected')}
📸 Photo: {'✅ Uploaded' if 'photo_data' in session else '❌ Not uploaded'}

📋 **Current Status:** {status_messages.get(status, status)}
"""
        
        if status == 'approved':
            status_text += "\n🚀 You can now use face recognition at the attendance kiosk!"
        elif status == 'rejected':
            status_text += "\n🔄 Use /register to start a new registration."
        
        await update.message.reply_text(status_text, parse_mode='Markdown')
    
    def validate_employee_id(self, employee_id: str) -> bool:
        """Validate employee ID format"""
        import re
        return bool(re.match(r'^[A-Za-z0-9]{3,10}$', employee_id))
    
    def validate_name(self, name: str) -> bool:
        """Validate name format"""
        import re
        return bool(re.match(r'^[A-Za-z\s]{2,50}$', name)) and len(name.split()) >= 2
    
    def validate_department(self, department: str) -> bool:
        """Validate department format"""
        import re
        return bool(re.match(r'^[A-Za-z\s]{2,30}$', department.strip()))
    
    def check_employee_id_exists(self, employee_id: str) -> bool:
        """Check if employee ID already exists in database"""
        try:
            employee = self.db.get_employee(employee_id.upper())
            return employee is not None
        except:
            return False
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle errors"""
        logger.error(f"Exception while handling an update: {context.error}")
    
    def run(self):
        """Run the bot"""
        # Create application
        application = Application.builder().token(self.token).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("register", self.register_command))
        application.add_handler(CommandHandler("status", self.status_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message))
        application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        application.add_handler(CallbackQueryHandler(self.handle_callback_query))
        
        # Add error handler
        application.add_error_handler(self.error_handler)
        
        # Start bot
        logger.info("Starting Telegram Registration Bot...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)