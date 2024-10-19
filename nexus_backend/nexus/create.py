from ninja import NinjaAPI, Router, File, Form, UploadedFile
from ninja.responses import Response
from .models import Post
from ninja_jwt.authentication import JWTAuth
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

create_router = NinjaAPI(urls_namespace='createAPI')

@create_router.post("/create-post", auth=JWTAuth())
def create_post(request, caption: str = Form(None), post_image: UploadedFile = File(...)) -> Response:

    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    # Save the uploaded image
    image_name = default_storage.save(f'media/uploads/{post_image.name}', ContentFile(post_image.read()))
    image_url = default_storage.url(image_name)

    # Create a new post instance
    post = Post.objects.create(
        user_id=request.user,
        caption=caption, 
        post_image=image_url 
    )

    return Response({
        "success": True,
        "message": "Post created successfully",
        "post_id": post.post_id,
        "post_image": image_url  
    }, status=201)
