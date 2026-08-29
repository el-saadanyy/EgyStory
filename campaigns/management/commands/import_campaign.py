import json
import zipfile
from decimal import Decimal
from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.conf import settings
from accounts.models import User
from campaigns.models import Campaign, Category, Tag, CampaignImage, CampaignStatus, CaseType


class Command(BaseCommand):
    help = "Safely imports a Campaign handoff ZIP package, creating a brand-new Campaign record without overwriting existing data."

    def add_arguments(self, parser):
        parser.add_argument(
            "package_path",
            type=str,
            help="Path to the campaign handoff ZIP package (e.g., handoff/campaign_123_handoff.zip).",
        )

    def handle(self, *args, **options):
        package_path = Path(options["package_path"]).resolve()

        if not package_path.is_file():
            raise CommandError(f"Package file not found: {package_path}")

        self.stdout.write(f"Validating and inspecting package: {package_path.name}...")

        media_root = Path(settings.MEDIA_ROOT).resolve()
        media_root.mkdir(parents=True, exist_ok=True)

        # ── Step 1: Strict ZIP & Path Traversal Validation ──────────────────
        raw_json_data = None
        media_members = []

        try:
            with zipfile.ZipFile(package_path, "r") as zip_file:
                for item in zip_file.infolist():
                    filename = item.filename

                    # Reject absolute paths or invalid characters
                    if filename.startswith("/") or filename.startswith("\\"):
                        raise CommandError(f"Security violation: Archive member has absolute path: '{filename}'")

                    # Normalize path separators
                    normalized_parts = filename.replace("\\", "/").split("/")
                    if ".." in normalized_parts or "." in normalized_parts:
                        raise CommandError(f"Security violation: Path traversal sequence detected: '{filename}'")

                    if filename == "campaign_data.json":
                        raw_json_data = zip_file.read(item.filename)
                    elif filename.startswith("media/") and not item.is_dir():
                        rel_path = filename[len("media/"):]
                        dest_file = (media_root / rel_path).resolve()

                        # Ensure target path stays strictly inside MEDIA_ROOT
                        if not dest_file.is_relative_to(media_root) or dest_file == media_root:
                            raise CommandError(f"Security violation: Target path escapes MEDIA_ROOT: '{filename}'")

                        media_members.append(item)
        except zipfile.BadZipFile:
            raise CommandError(f"File is not a valid ZIP archive: {package_path}")

        if not raw_json_data:
            raise CommandError("Invalid package: 'campaign_data.json' was not found inside the ZIP archive.")

        # ── Step 2: JSON Payload Validation ────────────────────────────────
        try:
            payload = json.loads(raw_json_data.decode("utf-8"))
        except Exception as e:
            raise CommandError(f"Invalid JSON in 'campaign_data.json': {str(e)}")

        required_keys = ["user", "campaign"]
        for key in required_keys:
            if key not in payload:
                raise CommandError(f"Malformed manifest: missing required section '{key}'.")

        user_data = payload.get("user") or {}
        camp_data = payload.get("campaign") or {}
        cat_data = payload.get("category")
        tags_data = payload.get("tags") or []
        gallery_data = payload.get("gallery_images") or []

        owner_email = (user_data.get("email") or "").strip().lower()
        if not owner_email:
            raise CommandError("Malformed manifest: 'user.email' is required.")

        campaign_title = (camp_data.get("title") or "").strip()
        campaign_story = (camp_data.get("story") or "").strip()
        if not campaign_title or not campaign_story:
            raise CommandError("Malformed manifest: campaign 'title' and 'story' are required.")

        try:
            target_amount = Decimal(str(camp_data.get("target_amount", "0.00")))
            initial_raised = Decimal(str(camp_data.get("initial_raised_amount", "0.00")))
            raised_amount = Decimal(str(camp_data.get("raised_amount", "0.00")))
        except Exception:
            raise CommandError("Malformed manifest: Invalid decimal number in campaign financial fields.")

        deadline_val = None
        if camp_data.get("deadline"):
            try:
                deadline_val = date.fromisoformat(camp_data["deadline"])
            except Exception:
                deadline_val = None

        # ── Step 3: Transactional Database Reconstruction ──────────────────
        new_campaign = None
        created_media_paths = []

        try:
            with transaction.atomic():
                # 3a. Resolve or create Owner User (safely by email without touching passwords of existing users)
                owner_user = User.objects.filter(email=owner_email).first()
                if not owner_user:
                    owner_user = User.objects.create(
                        email=owner_email,
                        first_name=user_data.get("first_name") or "Contributor",
                        last_name=user_data.get("last_name") or "",
                        phone=user_data.get("phone") or "01000000000",
                        is_active=True,
                    )
                    owner_user.set_unusable_password()
                    owner_user.save()
                    self.stdout.write(f"  + Created new User record for owner: {owner_user.email}")
                else:
                    self.stdout.write(f"  * Reusing existing User: {owner_user.email} (ID #{owner_user.id})")

                # 3b. Resolve or create Category (by slug/name)
                category_obj = None
                if cat_data and isinstance(cat_data, dict):
                    cat_name = cat_data.get("name")
                    cat_slug = cat_data.get("slug")
                    if cat_slug:
                        category_obj = Category.objects.filter(slug=cat_slug).first()
                    if not category_obj and cat_name:
                        category_obj = Category.objects.filter(name=cat_name).first()
                    if not category_obj and (cat_name or cat_slug):
                        category_obj = Category.objects.create(
                            name=cat_name or cat_slug,
                            slug=cat_slug or "",
                        )
                        self.stdout.write(f"  + Created Category: {category_obj.name}")

                # 3c. Resolve or create Tags (by slug/name)
                resolved_tags = []
                for t in tags_data:
                    if isinstance(t, dict):
                        t_name = t.get("name")
                        t_slug = t.get("slug")
                        tag_obj = None
                        if t_slug:
                            tag_obj = Tag.objects.filter(slug=t_slug).first()
                        if not tag_obj and t_name:
                            tag_obj = Tag.objects.filter(name=t_name).first()
                        if not tag_obj and (t_name or t_slug):
                            tag_obj = Tag.objects.create(
                                name=t_name or t_slug,
                                slug=t_slug or "",
                            )
                            self.stdout.write(f"  + Created Tag: #{tag_obj.name}")
                        if tag_obj:
                            resolved_tags.append(tag_obj)

                # 3d. Create BRAND-NEW Campaign (NEVER reuse source PK)
                new_campaign = Campaign(
                    owner=owner_user,
                    category=category_obj,
                    title=campaign_title,
                    story=campaign_story,
                    target_amount=target_amount,
                    initial_raised_amount=initial_raised,
                    raised_amount=raised_amount,
                    campaign_image=camp_data.get("campaign_image") or "",
                    case_type=camp_data.get("case_type") or CaseType.NORMAL,
                    status=camp_data.get("status") or CampaignStatus.PENDING,
                    deadline=deadline_val,
                    supporting_document=camp_data.get("supporting_document") or "",
                    is_manual_critical=bool(camp_data.get("is_manual_critical", False)),
                    is_featured=bool(camp_data.get("is_featured", False)),
                )
                new_campaign.save()

                # 3e. Attach M2M Tags
                if resolved_tags:
                    new_campaign.tags.set(resolved_tags)

                # 3f. Create CampaignImage Gallery Records
                for g_path in gallery_data:
                    if g_path and isinstance(g_path, str):
                        CampaignImage.objects.create(
                            campaign=new_campaign,
                            image=g_path,
                        )

                # ── Step 4: Extract Media Files Safely ─────────────────────────
                with zipfile.ZipFile(package_path, "r") as zip_file:
                    for member in media_members:
                        rel_path = member.filename[len("media/"):]
                        dest_file = (media_root / rel_path).resolve()
                        dest_file.parent.mkdir(parents=True, exist_ok=True)

                        is_new_file = not dest_file.exists()
                        with open(dest_file, "wb") as f_out:
                            f_out.write(zip_file.read(member.filename))

                        if is_new_file:
                            created_media_paths.append(dest_file)

        except Exception as e:
            # Clean up newly extracted files if the transaction fails
            for f_path in created_media_paths:
                try:
                    if f_path.is_file():
                        f_path.unlink()
                except Exception:
                    pass
            raise CommandError(f"Database import failed (rolled back safely): {str(e)}")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSuccessfully imported campaign as a brand-new record!\n"
                f"  - New Campaign ID: #{new_campaign.id}\n"
                f"  - Title: '{new_campaign.title}'\n"
                f"  - Owner: {new_campaign.owner.email}\n"
                f"  - Status: '{new_campaign.status}'\n"
                f"  - Media files extracted: {len(media_members)}\n"
                f"  - Note: If status is 'Pending Review', approve it at http://127.0.0.1:8000/admin-panel/campaigns/."
            )
        )
