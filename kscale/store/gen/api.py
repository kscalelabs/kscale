"""Auto-generated by generate.sh script."""

# generated by datamodel-codegen:
#   filename:  openapi.json
#   timestamp: 2024-09-04T04:33:58+00:00

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, EmailStr, Field


class ArtifactUrls(BaseModel):
    small: Optional[str] = Field(None, title="Small")
    large: str = Field(..., title="Large")


class AuthResponse(BaseModel):
    api_key: str = Field(..., title="Api Key")


class BodyPullOnshapeDocumentOnshapePullListingIdGet(BaseModel):
    suffix_to_joint_effort: Optional[Dict[str, float]] = Field(None, title="Suffix To Joint Effort")
    suffix_to_joint_velocity: Optional[Dict[str, float]] = Field(None, title="Suffix To Joint Velocity")


class BodyUploadArtifactsUploadListingIdPost(BaseModel):
    files: List[bytes] = Field(..., title="Files")


class ClientIdResponse(BaseModel):
    client_id: str = Field(..., title="Client Id")


class DeleteTokenResponse(BaseModel):
    message: str = Field(..., title="Message")


class EmailSignUpRequest(BaseModel):
    email: EmailStr = Field(..., title="Email")


class EmailSignUpResponse(BaseModel):
    message: str = Field(..., title="Message")


class GetListingResponse(BaseModel):
    id: str = Field(..., title="Id")
    name: str = Field(..., title="Name")
    description: Optional[str] = Field(..., title="Description")
    child_ids: List[str] = Field(..., title="Child Ids")
    tags: List[str] = Field(..., title="Tags")
    onshape_url: Optional[str] = Field(..., title="Onshape Url")
    can_edit: bool = Field(..., title="Can Edit")
    created_at: int = Field(..., title="Created At")
    views: int = Field(..., title="Views")
    score: int = Field(..., title="Score")
    user_vote: Optional[bool] = Field(..., title="User Vote")
    creator_id: str = Field(..., title="Creator Id")


class GetTokenResponse(BaseModel):
    id: str = Field(..., title="Id")
    email: str = Field(..., title="Email")


class GithubAuthRequest(BaseModel):
    code: str = Field(..., title="Code")


class GithubAuthResponse(BaseModel):
    api_key: str = Field(..., title="Api Key")


class GoogleLogin(BaseModel):
    token: str = Field(..., title="Token")


class Permission(Enum):
    read = "read"
    write = "write"
    admin = "admin"


class KeysResponseItem(BaseModel):
    token: str = Field(..., title="Token")
    permissions: Optional[List[Permission]] = Field(..., title="Permissions")


class ListKeysResponse(BaseModel):
    keys: List[KeysResponseItem] = Field(..., title="Keys")


class ListListingsResponse(BaseModel):
    listing_ids: List[str] = Field(..., title="Listing Ids")
    has_next: Optional[bool] = Field(False, title="Has Next")


class Listing(BaseModel):
    id: str = Field(..., title="Id")
    user_id: str = Field(..., title="User Id")
    created_at: int = Field(..., title="Created At")
    updated_at: int = Field(..., title="Updated At")
    name: str = Field(..., title="Name")
    child_ids: List[str] = Field(..., title="Child Ids")
    description: Optional[str] = Field(None, title="Description")
    onshape_url: Optional[str] = Field(None, title="Onshape Url")
    views: Optional[int] = Field(0, title="Views")
    upvotes: Optional[int] = Field(0, title="Upvotes")
    downvotes: Optional[int] = Field(0, title="Downvotes")
    score: Optional[int] = Field(0, title="Score")


class ListingInfoResponse(BaseModel):
    id: str = Field(..., title="Id")
    name: str = Field(..., title="Name")
    description: Optional[str] = Field(..., title="Description")
    child_ids: List[str] = Field(..., title="Child Ids")
    image_url: Optional[str] = Field(..., title="Image Url")
    onshape_url: Optional[str] = Field(..., title="Onshape Url")
    created_at: int = Field(..., title="Created At")
    views: int = Field(..., title="Views")
    score: int = Field(..., title="Score")
    user_vote: Optional[bool] = Field(..., title="User Vote")


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., title="Email")
    password: str = Field(..., title="Password")


class LoginResponse(BaseModel):
    user_id: str = Field(..., title="User Id")
    token: str = Field(..., title="Token")


class Permission1(Enum):
    is_admin = "is_admin"


class MyUserInfoResponse(BaseModel):
    user_id: str = Field(..., title="User Id")
    email: str = Field(..., title="Email")
    github_id: Optional[str] = Field(..., title="Github Id")
    google_id: Optional[str] = Field(..., title="Google Id")
    permissions: Optional[List[Permission1]] = Field(..., title="Permissions")
    first_name: Optional[str] = Field(..., title="First Name")
    last_name: Optional[str] = Field(..., title="Last Name")
    name: Optional[str] = Field(..., title="Name")
    bio: Optional[str] = Field(..., title="Bio")


class NewKeyRequest(BaseModel):
    readonly: Optional[bool] = Field(True, title="Readonly")


class NewKeyResponse(BaseModel):
    user_id: str = Field(..., title="User Id")
    key: KeysResponseItem


class NewListingRequest(BaseModel):
    name: str = Field(..., title="Name")
    child_ids: List[str] = Field(..., title="Child Ids")
    description: Optional[str] = Field(..., title="Description")


class NewListingResponse(BaseModel):
    listing_id: str = Field(..., title="Listing Id")


class PublicUserInfoResponseItem(BaseModel):
    id: str = Field(..., title="Id")
    email: str = Field(..., title="Email")
    permissions: Optional[List[Permission1]] = Field(None, title="Permissions")
    created_at: Optional[int] = Field(None, title="Created At")
    updated_at: Optional[int] = Field(None, title="Updated At")
    first_name: Optional[str] = Field(None, title="First Name")
    last_name: Optional[str] = Field(None, title="Last Name")
    name: Optional[str] = Field(None, title="Name")
    bio: Optional[str] = Field(None, title="Bio")


class PublicUsersInfoResponse(BaseModel):
    users: List[PublicUserInfoResponseItem] = Field(..., title="Users")


class SetRequest(BaseModel):
    onshape_url: Optional[str] = Field(..., title="Onshape Url")


class ArtifactType(Enum):
    image = "image"


class ArtifactType1(Enum):
    urdf = "urdf"
    mjcf = "mjcf"


class ArtifactType2(Enum):
    stl = "stl"
    obj = "obj"
    dae = "dae"
    ply = "ply"


class ArtifactType3(Enum):
    tgz = "tgz"
    zip = "zip"


class SingleArtifactResponse(BaseModel):
    artifact_id: str = Field(..., title="Artifact Id")
    listing_id: str = Field(..., title="Listing Id")
    name: str = Field(..., title="Name")
    artifact_type: Union[ArtifactType, ArtifactType1, ArtifactType2, ArtifactType3] = Field(..., title="Artifact Type")
    description: Optional[str] = Field(..., title="Description")
    timestamp: int = Field(..., title="Timestamp")
    urls: ArtifactUrls
    is_new: Optional[bool] = Field(None, title="Is New")


class SortOption(Enum):
    newest = "newest"
    most_viewed = "most_viewed"
    most_upvoted = "most_upvoted"


class UpdateArtifactRequest(BaseModel):
    name: Optional[str] = Field(None, title="Name")
    description: Optional[str] = Field(None, title="Description")


class UpdateListingRequest(BaseModel):
    name: Optional[str] = Field(None, title="Name")
    child_ids: Optional[List[str]] = Field(None, title="Child Ids")
    description: Optional[str] = Field(None, title="Description")
    tags: Optional[List[str]] = Field(None, title="Tags")


class UpdateUserRequest(BaseModel):
    email: Optional[str] = Field(None, title="Email")
    password: Optional[str] = Field(None, title="Password")
    github_id: Optional[str] = Field(None, title="Github Id")
    google_id: Optional[str] = Field(None, title="Google Id")
    first_name: Optional[str] = Field(None, title="First Name")
    last_name: Optional[str] = Field(None, title="Last Name")
    name: Optional[str] = Field(None, title="Name")
    bio: Optional[str] = Field(None, title="Bio")


class UploadArtifactResponse(BaseModel):
    artifacts: List[SingleArtifactResponse] = Field(..., title="Artifacts")


class UserInfoResponseItem(BaseModel):
    id: str = Field(..., title="Id")
    email: str = Field(..., title="Email")


class UserPublic(BaseModel):
    id: str = Field(..., title="Id")
    email: str = Field(..., title="Email")
    permissions: Optional[List[Permission1]] = Field(None, title="Permissions")
    created_at: int = Field(..., title="Created At")
    updated_at: Optional[int] = Field(None, title="Updated At")
    first_name: Optional[str] = Field(None, title="First Name")
    last_name: Optional[str] = Field(None, title="Last Name")
    name: Optional[str] = Field(None, title="Name")
    bio: Optional[str] = Field(None, title="Bio")


class UserSignup(BaseModel):
    signup_token_id: str = Field(..., title="Signup Token Id")
    email: str = Field(..., title="Email")
    password: str = Field(..., title="Password")


class ValidationError(BaseModel):
    loc: List[Union[str, int]] = Field(..., title="Location")
    msg: str = Field(..., title="Message")
    type: str = Field(..., title="Error Type")


class DumpListingsResponse(BaseModel):
    listings: List[Listing] = Field(..., title="Listings")


class GetBatchListingsResponse(BaseModel):
    listings: List[ListingInfoResponse] = Field(..., title="Listings")


class HTTPValidationError(BaseModel):
    detail: Optional[List[ValidationError]] = Field(None, title="Detail")


class ListArtifactsResponse(BaseModel):
    artifacts: List[SingleArtifactResponse] = Field(..., title="Artifacts")
