from django import forms

from academics.forms import BootstrapFormMixin

from .models import SiteSetting


class SiteSettingForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = SiteSetting
        fields = [
            "institution_name",
            "institution_tagline",
            "address",
            "pass_percentage",
            "require_pass_in_every_subject",
            "absent_counts_as_fail",
            "fail_zeroes_gpa",
            "show_position",
            "section_wise_highest",
            "result_footer_note",
        ]
