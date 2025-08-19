"""Manager for handling Hinge prompts."""

from hinge_enums import ContentType
from hinge_models import Prompt, PromptCategory, PromptsResponse


class HingePromptsManager:
    """Manager class for handling prompts data and queries."""

    def __init__(self, prompts_data: PromptsResponse):
        """Initialize the PromptsManager with the current prompts.

        Args:
            prompts_data (PromptsResponse): Data containing prompts and their details.

        """
        self.prompts_data = prompts_data
        self._prompts_by_id = {p.id: p for p in prompts_data.prompts}
        self._categories_by_slug = {c.slug: c for c in prompts_data.categories}

    def get_prompt_by_id(self, prompt_id: str) -> Prompt | None:
        """Get a prompt by its ID."""
        return self._prompts_by_id.get(prompt_id)

    def get_category_by_slug(self, slug: str) -> PromptCategory | None:
        """Get a category by its slug."""
        return self._categories_by_slug.get(slug)

    def get_prompts_by_category(self, category_slug: str) -> list[Prompt]:
        """Get all prompts belonging to a specific category."""
        return [p for p in self.prompts_data.prompts if category_slug in p.categories]

    def get_prompts_by_content_type(self, content_type: ContentType) -> list[Prompt]:
        """Get all prompts that support a specific content type."""
        return [
            p for p in self.prompts_data.prompts if content_type in p.content_types
        ]

    def get_selectable_prompts(self) -> list[Prompt]:
        """Get all selectable prompts."""
        return [p for p in self.prompts_data.prompts if p.is_selectable]

    def get_new_prompts(self) -> list[Prompt]:
        """Get all new prompts."""
        return [p for p in self.prompts_data.prompts if p.is_new]

    def get_text_prompts(self) -> list[Prompt]:
        """Get all prompts that support text responses."""
        return self.get_prompts_by_content_type(ContentType.TEXT)

    def get_media_prompts(self) -> list[Prompt]:
        """Get all prompts that support media responses."""
        return self.get_prompts_by_content_type(ContentType.MEDIA)

    def search_prompts(self, query: str) -> list[Prompt]:
        """Search prompts by text content."""
        query_lower = query.lower()
        return [
            p
            for p in self.prompts_data.prompts
            if query_lower in p.prompt.lower() or query_lower in p.placeholder.lower()
        ]

    def get_prompt_display_text(self, prompt_id: str) -> str:
        """Get the display text for a prompt (for backwards compatibility)."""
        prompt = self.get_prompt_by_id(prompt_id)
        return prompt.prompt if prompt else "Unknown Question"

    def get_visible_categories(self) -> list[PromptCategory]:
        """Get all visible categories."""
        return [c for c in self.prompts_data.categories if c.is_visible]

    def export_to_json(self) -> dict:
        """Export prompts data to JSON format."""
        return self.prompts_data.model_dump()
