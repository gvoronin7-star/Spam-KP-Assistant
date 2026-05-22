"""
Сервис экспорта и импорта данных
"""
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
from sqlalchemy.orm import Session
from loguru import logger

from core.models import Profile, Contact, Template, Dialogue, Message, Task


class DataExportImportService:
    """Сервис для экспорта/импорта данных"""
    
    def export_json(self, db: Session, filepath: str, entities: Optional[List[str]] = None) -> Dict:
        """
        Экспортировать данные в JSON
        
        Args:
            db: Сессия БД
            filepath: Путь к файлу
            entities: Список сущностей для экспорта (all, profiles, contacts, templates, dialogues, tasks)
        
        Returns:
            Статистика экспорта
        """
        entities = entities or ["all"]
        data = {"export_date": datetime.now().isoformat(), "version": "1.0"}
        stats = {}
        
        if "all" in entities or "profiles" in entities:
            profiles = db.query(Profile).filter_by(is_active=True).all()
            data["profiles"] = [self._profile_to_dict(p) for p in profiles]
            stats["profiles"] = len(profiles)
        
        if "all" in entities or "contacts" in entities:
            contacts = db.query(Contact).filter_by(is_active=True).all()
            data["contacts"] = [self._contact_to_dict(c) for c in contacts]
            stats["contacts"] = len(contacts)
        
        if "all" in entities or "templates" in entities:
            templates = db.query(Template).filter_by(is_active=True).all()
            data["templates"] = [self._template_to_dict(t) for t in templates]
            stats["templates"] = len(templates)
        
        if "all" in entities or "dialogues" in entities:
            dialogues = db.query(Dialogue).all()
            data["dialogues"] = [self._dialogue_to_dict(d, db) for d in dialogues]
            stats["dialogues"] = len(dialogues)
        
        if "all" in entities or "tasks" in entities:
            tasks = db.query(Task).filter_by(is_completed=False).all()
            data["tasks"] = [self._task_to_dict(t) for t in tasks]
            stats["tasks"] = len(tasks)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Экспорт JSON: {filepath} — {stats}")
        return {"filepath": filepath, "stats": stats}
    
    def export_xml(self, db: Session, filepath: str, entities: Optional[List[str]] = None) -> Dict:
        """
        Экспортировать данные в XML
        
        Args:
            db: Сессия БД
            filepath: Путь к файлу
            entities: Список сущностей
        
        Returns:
            Статистика экспорта
        """
        entities = entities or ["all"]
        root = ET.Element("spam_kp_export")
        root.set("version", "1.0")
        root.set("date", datetime.now().isoformat())
        
        stats = {}
        
        if "all" in entities or "profiles" in entities:
            profiles = db.query(Profile).filter_by(is_active=True).all()
            profiles_el = ET.SubElement(root, "profiles")
            for p in profiles:
                self._profile_to_xml(p, profiles_el)
            stats["profiles"] = len(profiles)
        
        if "all" in entities or "contacts" in entities:
            contacts = db.query(Contact).filter_by(is_active=True).all()
            contacts_el = ET.SubElement(root, "contacts")
            for c in contacts:
                self._contact_to_xml(c, contacts_el)
            stats["contacts"] = len(contacts)
        
        if "all" in entities or "templates" in entities:
            templates = db.query(Template).filter_by(is_active=True).all()
            templates_el = ET.SubElement(root, "templates")
            for t in templates:
                self._template_to_xml(t, templates_el)
            stats["templates"] = len(templates)
        
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")
        tree.write(filepath, encoding='utf-8', xml_declaration=True)
        
        logger.info(f"Экспорт XML: {filepath} — {stats}")
        return {"filepath": filepath, "stats": stats}
    
    def import_json(self, db: Session, filepath: str, overwrite: bool = False) -> Dict:
        """
        Импортировать данные из JSON
        
        Args:
            db: Сессия БД
            filepath: Путь к файлу
            overwrite: Перезаписывать существующие
        
        Returns:
            Статистика импорта
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        stats = {"created": 0, "updated": 0, "errors": 0}
        
        # Импорт профилей
        for p_data in data.get("profiles", []):
            try:
                existing = db.query(Profile).filter_by(name=p_data["name"]).first()
                if existing and overwrite:
                    for key, value in p_data.items():
                        if hasattr(existing, key) and key != "id":
                            setattr(existing, key, value)
                    stats["updated"] += 1
                elif not existing:
                    profile = Profile(**{k: v for k, v in p_data.items() if k != "id"})
                    db.add(profile)
                    stats["created"] += 1
            except Exception as e:
                logger.error(f"Ошибка импорта профиля {p_data.get('name')}: {e}")
                stats["errors"] += 1
        
        # Импорт контактов
        for c_data in data.get("contacts", []):
            try:
                existing = db.query(Contact).filter_by(email=c_data["email"]).first()
                if existing and overwrite:
                    for key, value in c_data.items():
                        if hasattr(existing, key) and key != "id":
                            setattr(existing, key, value)
                    stats["updated"] += 1
                elif not existing:
                    contact = Contact(**{k: v for k, v in c_data.items() if k != "id"})
                    db.add(contact)
                    stats["created"] += 1
            except Exception as e:
                logger.error(f"Ошибка импорта контакта {c_data.get('email')}: {e}")
                stats["errors"] += 1
        
        # Импорт шаблонов
        for t_data in data.get("templates", []):
            try:
                existing = db.query(Template).filter_by(name=t_data["name"]).first()
                if existing and overwrite:
                    for key, value in t_data.items():
                        if hasattr(existing, key) and key != "id":
                            setattr(existing, key, value)
                    stats["updated"] += 1
                elif not existing:
                    template = Template(**{k: v for k, v in t_data.items() if k != "id"})
                    db.add(template)
                    stats["created"] += 1
            except Exception as e:
                logger.error(f"Ошибка импорта шаблона {t_data.get('name')}: {e}")
                stats["errors"] += 1
        
        db.commit()
        logger.info(f"Импорт JSON: {filepath} — {stats}")
        return stats
    
    def _profile_to_dict(self, p: Profile) -> Dict:
        return {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "tech_params": p.tech_params,
            "requirements": p.requirements,
            "is_active": p.is_active
        }
    
    def _contact_to_dict(self, c: Contact) -> Dict:
        return {
            "id": c.id,
            "email": c.email,
            "company_name": c.company_name,
            "contact_person": c.contact_person,
            "notes": c.notes,
            "is_active": c.is_active
        }
    
    def _template_to_dict(self, t: Template) -> Dict:
        return {
            "id": t.id,
            "name": t.name,
            "template_type": t.template_type,
            "subject": t.subject,
            "body_plain": t.body_plain,
            "body_html": t.body_html,
            "attachments": t.attachments,
            "is_active": t.is_active
        }
    
    def _dialogue_to_dict(self, d: Dialogue, db: Session) -> Dict:
        messages = db.query(Message).filter_by(dialogue_id=d.id).all()
        return {
            "id": d.id,
            "contact_email": d.contact.email if d.contact else None,
            "profile_name": d.profile.name if d.profile else None,
            "status": d.status,
            "kp_received": d.kp_received,
            "messages": [
                {
                    "direction": m.direction,
                    "subject": m.subject,
                    "body_plain": m.body_plain,
                    "created_at": m.created_at.isoformat() if m.created_at else None
                }
                for m in messages
            ]
        }
    
    def _task_to_dict(self, t: Task) -> Dict:
        return {
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "task_type": t.task_type,
            "priority": t.priority,
            "due_date": t.due_date.isoformat() if t.due_date else None,
            "is_completed": t.is_completed
        }
    
    def _profile_to_xml(self, p: Profile, parent: ET.Element):
        el = ET.SubElement(parent, "profile")
        ET.SubElement(el, "name").text = p.name
        ET.SubElement(el, "description").text = p.description or ""
        ET.SubElement(el, "tech_params").text = json.dumps(p.tech_params or {})
    
    def _contact_to_xml(self, c: Contact, parent: ET.Element):
        el = ET.SubElement(parent, "contact")
        ET.SubElement(el, "email").text = c.email
        ET.SubElement(el, "company_name").text = c.company_name or ""
        ET.SubElement(el, "contact_person").text = c.contact_person or ""
    
    def _template_to_xml(self, t: Template, parent: ET.Element):
        el = ET.SubElement(parent, "template")
        ET.SubElement(el, "name").text = t.name
        ET.SubElement(el, "template_type").text = t.template_type or ""
        ET.SubElement(el, "subject").text = t.subject or ""
