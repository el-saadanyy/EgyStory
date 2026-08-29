import json
import zipfile
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from campaigns.models import Campaign


class Command(BaseCommand):
    help = "Exports a specific Campaign, its required dependencies, and referenced media files into a portable, safe JSON ZIP package."

    def add_arguments(self, parser):
        parser.add_argument(
            "campaign_id",
            type=int,
            help="The ID (PK) of the Campaign to export.",
        )
        parser.add_argument(
            "--output-dir",
            type=str,
            default="handoff",
            help="Directory where the exported package should be saved (default: 'handoff').",
        )

    def handle(self, *args, **options):
        campaign_id = options["campaign_id"]
        output_dir = Path(options["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            campaign = Campaign.objects.select_related("owner", "category").prefetch_related("tags", "images").get(id=campaign_id)
        except Campaign.DoesNotExist:
            raise CommandError(f"Campaign with ID {campaign_id} does not exist.")

        self.stdout.write(f"Packaging Campaign #{campaign.id}: '{campaign.title}' (Owner: {campaign.owner.email})...")

        # 1. Structure explicit payload without assigning PKs as identity
        owner = campaign.owner
        user_payload = {
            "email": owner.email,
            "first_name": owner.first_name,
            "last_name": owner.last_name,
            "phone": owner.phone,
            "is_active": owner.is_active,
        }

        category_payload = None
        if campaign.category:
            category_payload = {
                "name": campaign.category.name,
                "slug": campaign.category.slug,
            }

        tags_payload = []
        for tag in campaign.tags.all():
            tags_payload.append({
                "name": tag.name,
                "slug": tag.slug,
            })

        campaign_payload = {
            "title": campaign.title,
            "story": campaign.story,
            "target_amount": str(campaign.target_amount),
            "initial_raised_amount": str(campaign.initial_raised_amount) if campaign.initial_raised_amount is not None else "0.00",
            "raised_amount": str(campaign.raised_amount),
            "campaign_image": campaign.campaign_image.name if campaign.campaign_image else "",
            "case_type": campaign.case_type,
            "status": campaign.status,
            "deadline": campaign.deadline.isoformat() if campaign.deadline else None,
            "supporting_document": campaign.supporting_document.name if campaign.supporting_document else "",
            "is_manual_critical": campaign.is_manual_critical,
            "is_featured": campaign.is_featured,
        }

        gallery_images_payload = []
        for gallery_img in campaign.images.all():
            if gallery_img.image and gallery_img.image.name:
                gallery_images_payload.append(gallery_img.image.name)

        manifest = {
            "version": "1.0",
            "source_campaign_id": campaign.id,
            "user": user_payload,
            "category": category_payload,
            "tags": tags_payload,
            "campaign": campaign_payload,
            "gallery_images": gallery_images_payload,
        }

        json_data = json.dumps(manifest, indent=2, ensure_ascii=False)

        package_name = f"campaign_{campaign.id}_handoff"
        zip_path = output_dir / f"{package_name}.zip"

        # 2. Package data and referenced physical media files
        media_root = Path(settings.MEDIA_ROOT)
        packaged_files_count = 0

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # Write campaign_data.json
            zip_file.writestr("campaign_data.json", json_data.encode("utf-8"))

            # Primary cover image
            if campaign.campaign_image and campaign.campaign_image.name:
                img_path = media_root / campaign.campaign_image.name
                if img_path.is_file():
                    zip_file.write(img_path, arcname=f"media/{campaign.campaign_image.name}")
                    packaged_files_count += 1
                else:
                    self.stdout.write(self.style.WARNING(f"Cover image file not found on disk: {img_path}"))

            # Supporting document
            if campaign.supporting_document and campaign.supporting_document.name:
                doc_path = media_root / campaign.supporting_document.name
                if doc_path.is_file():
                    zip_file.write(doc_path, arcname=f"media/{campaign.supporting_document.name}")
                    packaged_files_count += 1
                else:
                    self.stdout.write(self.style.WARNING(f"Supporting document not found on disk: {doc_path}"))

            # Gallery images
            for g_name in gallery_images_payload:
                g_path = media_root / g_name
                if g_path.is_file():
                    zip_file.write(g_path, arcname=f"media/{g_name}")
                    packaged_files_count += 1
                else:
                    self.stdout.write(self.style.WARNING(f"Gallery image not found on disk: {g_path}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully exported Campaign #{campaign.id} to {zip_path}\n"
                f"  - Package: {zip_path.resolve()}\n"
                f"  - Tags included: {len(tags_payload)}\n"
                f"  - Media files included: {packaged_files_count}"
            )
        )
