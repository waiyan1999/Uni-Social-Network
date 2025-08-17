# forms.py
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm,AuthenticationForm
from .models import Post, Comment, Profile


User = get_user_model()

class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("email", "password1", "password2")

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("A user with that email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].strip().lower()
        if commit:
            user.save()
        return user


class EmailAuthenticationForm(AuthenticationForm):
    """
    AuthenticationForm uses USERNAME_FIELD label automatically,
    but we make it an EmailField so the input gets type="email".
    """
    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"autocomplete": "email"})
    )



class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ["text", "photo"]

    def clean(self):
        data = super().clean()
        if not data.get("text") and not data.get("photo"):
            raise forms.ValidationError("Post must have text, photo, or both.")
        return data


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["body"]


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["full_name", "bio", "major", "year", "roll_no", "photo", "phone_no"]


