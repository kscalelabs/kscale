"""Auto-generated by generate.sh script."""

# generated by datamodel-codegen:
#   filename:  openapi.json
#   timestamp: 2024-11-22T23:25:21+00:00

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, EmailStr, Field


class ArtifactUrls(BaseModel):
    small: Optional[str] = Field(None, title="Small")
    large: str = Field(..., title="Large")
    expires_at: int = Field(..., title="Expires At")


class AuthResponse(BaseModel):
    api_key: str = Field(..., title="Api Key")


class InventoryType(Enum):
    finite = "finite"
    preorder = "preorder"


class BodyAddListingListingsAddPost(BaseModel):
    name: str = Field(..., title="Name")
    description: Optional[str] = Field(None, title="Description")
    child_ids: Optional[str] = Field("", title="Child Ids")
    slug: str = Field(..., title="Slug")
    price_amount: Optional[str] = Field(None, title="Price Amount")
    currency: Optional[str] = Field("usd", title="Currency")
    inventory_type: Optional[InventoryType] = Field("finite", title="Inventory Type")
    inventory_quantity: Optional[str] = Field(None, title="Inventory Quantity")
    preorder_deposit_amount: Optional[str] = Field(None, title="Preorder Deposit Amount")
    preorder_release_date: Optional[str] = Field(None, title="Preorder Release Date")
    photos: Optional[List[bytes]] = Field(None, title="Photos")


class BodyCreateConnectAccountSessionStripeConnectAccountSessionPost(BaseModel):
    account_id: str = Field(..., title="Account Id")


class BodyPullOnshapeDocumentOnshapePullListingIdGet(BaseModel):
    suffix_to_joint_effort: Optional[Dict[str, float]] = Field(None, title="Suffix To Joint Effort")
    suffix_to_joint_velocity: Optional[Dict[str, float]] = Field(None, title="Suffix To Joint Velocity")


class BodyUploadArtifactsUploadListingIdPost(BaseModel):
    files: List[bytes] = Field(..., title="Files")


class CancelReason(BaseModel):
    reason: str = Field(..., title="Reason")
    details: str = Field(..., title="Details")


class ClientIdResponse(BaseModel):
    client_id: str = Field(..., title="Client Id")


class CreateCheckoutSessionRequest(BaseModel):
    listing_id: str = Field(..., title="Listing Id")
    stripe_product_id: str = Field(..., title="Stripe Product Id")
    cancel_url: str = Field(..., title="Cancel Url")


class CreateCheckoutSessionResponse(BaseModel):
    session_id: str = Field(..., title="Session Id")
    stripe_connect_account_id: str = Field(..., title="Stripe Connect Account Id")


class CreateConnectAccountResponse(BaseModel):
    account_id: str = Field(..., title="Account Id")


class CreateRefundsRequest(BaseModel):
    payment_intent_id: str = Field(..., title="Payment Intent Id")
    cancel_reason: CancelReason
    amount: int = Field(..., title="Amount")


class CreateRobotRequest(BaseModel):
    listing_id: str = Field(..., title="Listing Id")
    name: str = Field(..., title="Name")
    description: Optional[str] = Field(None, title="Description")
    order_id: Optional[str] = Field(None, title="Order Id")


class DeleteTestAccountsResponse(BaseModel):
    success: bool = Field(..., title="Success")
    deleted_accounts: List[str] = Field(..., title="Deleted Accounts")
    count: int = Field(..., title="Count")


class DeleteTokenResponse(BaseModel):
    message: str = Field(..., title="Message")


class EmailSignUpRequest(BaseModel):
    email: EmailStr = Field(..., title="Email")


class EmailSignUpResponse(BaseModel):
    message: str = Field(..., title="Message")


class FeaturedListingsResponse(BaseModel):
    listing_ids: List[str] = Field(..., title="Listing Ids")


class GetTokenResponse(BaseModel):
    id: str = Field(..., title="Id")
    email: str = Field(..., title="Email")


class GithubAuthRequest(BaseModel):
    code: str = Field(..., title="Code")


class GithubAuthResponse(BaseModel):
    api_key: str = Field(..., title="Api Key")


class GoogleLogin(BaseModel):
    token: str = Field(..., title="Token")


class KRec(BaseModel):
    id: str = Field(..., title="Id")
    user_id: str = Field(..., title="User Id")
    robot_id: str = Field(..., title="Robot Id")
    created_at: int = Field(..., title="Created At")
    name: str = Field(..., title="Name")
    description: Optional[str] = Field(None, title="Description")


class KRecUrls(BaseModel):
    url: str = Field(..., title="Url")
    filename: str = Field(..., title="Filename")
    expires_at: int = Field(..., title="Expires At")
    checksum: Optional[str] = Field(None, title="Checksum")


class Permission(Enum):
    read = "read"
    write = "write"
    admin = "admin"


class KeysResponseItem(BaseModel):
    token: str = Field(..., title="Token")
    permissions: Optional[List[Permission]] = Field(..., title="Permissions")


class ListKeysResponse(BaseModel):
    keys: List[KeysResponseItem] = Field(..., title="Keys")


class Listing(BaseModel):
    id: str = Field(..., title="Id")
    user_id: str = Field(..., title="User Id")
    created_at: int = Field(..., title="Created At")
    updated_at: int = Field(..., title="Updated At")
    name: str = Field(..., title="Name")
    slug: str = Field(..., title="Slug")
    child_ids: List[str] = Field(..., title="Child Ids")
    description: Optional[str] = Field(None, title="Description")
    onshape_url: Optional[str] = Field(None, title="Onshape Url")
    views: Optional[int] = Field(0, title="Views")
    score: Optional[int] = Field(0, title="Score")
    price_amount: Optional[int] = Field(None, title="Price Amount")
    currency: Optional[str] = Field("usd", title="Currency")
    stripe_product_id: Optional[str] = Field(None, title="Stripe Product Id")
    stripe_price_id: Optional[str] = Field(None, title="Stripe Price Id")
    preorder_deposit_amount: Optional[int] = Field(None, title="Preorder Deposit Amount")
    stripe_preorder_deposit_id: Optional[str] = Field(None, title="Stripe Preorder Deposit Id")
    inventory_type: Optional[InventoryType] = Field("finite", title="Inventory Type")
    inventory_quantity: Optional[int] = Field(None, title="Inventory Quantity")
    preorder_release_date: Optional[int] = Field(None, title="Preorder Release Date")


class ListingInfo(BaseModel):
    id: str = Field(..., title="Id")
    username: str = Field(..., title="Username")
    slug: Optional[str] = Field(..., title="Slug")


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., title="Email")
    password: str = Field(..., title="Password")


class LoginResponse(BaseModel):
    user_id: str = Field(..., title="User Id")
    token: str = Field(..., title="Token")


class Permission1(Enum):
    is_admin = "is_admin"
    is_mod = "is_mod"
    is_content_manager = "is_content_manager"


class NewKeyRequest(BaseModel):
    readonly: Optional[bool] = Field(True, title="Readonly")


class NewKeyResponse(BaseModel):
    user_id: str = Field(..., title="User Id")
    key: KeysResponseItem


class NewListingResponse(BaseModel):
    listing_id: str = Field(..., title="Listing Id")
    username: str = Field(..., title="Username")
    slug: str = Field(..., title="Slug")


class Status(Enum):
    processing = "processing"
    in_development = "in_development"
    being_assembled = "being_assembled"
    shipped = "shipped"
    delivered = "delivered"
    preorder_placed = "preorder_placed"
    awaiting_final_payment = "awaiting_final_payment"
    cancelled = "cancelled"
    refunded = "refunded"


class Order(BaseModel):
    id: str = Field(..., title="Id")
    user_id: str = Field(..., title="User Id")
    listing_id: str = Field(..., title="Listing Id")
    user_email: str = Field(..., title="User Email")
    created_at: int = Field(..., title="Created At")
    updated_at: int = Field(..., title="Updated At")
    status: Status = Field(..., title="Status")
    price_amount: int = Field(..., title="Price Amount")
    currency: str = Field(..., title="Currency")
    quantity: int = Field(..., title="Quantity")
    stripe_checkout_session_id: str = Field(..., title="Stripe Checkout Session Id")
    stripe_connect_account_id: str = Field(..., title="Stripe Connect Account Id")
    stripe_product_id: str = Field(..., title="Stripe Product Id")
    stripe_price_id: str = Field(..., title="Stripe Price Id")
    stripe_payment_intent_id: str = Field(..., title="Stripe Payment Intent Id")
    preorder_release_date: Optional[int] = Field(None, title="Preorder Release Date")
    preorder_deposit_amount: Optional[int] = Field(None, title="Preorder Deposit Amount")
    stripe_preorder_deposit_id: Optional[str] = Field(None, title="Stripe Preorder Deposit Id")
    inventory_type: InventoryType = Field(..., title="Inventory Type")
    final_payment_checkout_session_id: Optional[str] = Field(None, title="Final Payment Checkout Session Id")
    final_payment_intent_id: Optional[str] = Field(None, title="Final Payment Intent Id")
    final_payment_date: Optional[int] = Field(None, title="Final Payment Date")
    shipping_name: Optional[str] = Field(None, title="Shipping Name")
    shipping_address_line1: Optional[str] = Field(None, title="Shipping Address Line1")
    shipping_address_line2: Optional[str] = Field(None, title="Shipping Address Line2")
    shipping_city: Optional[str] = Field(None, title="Shipping City")
    shipping_state: Optional[str] = Field(None, title="Shipping State")
    shipping_postal_code: Optional[str] = Field(None, title="Shipping Postal Code")
    shipping_country: Optional[str] = Field(None, title="Shipping Country")
    shipped_date: Optional[int] = Field(None, title="Shipped Date")
    stripe_refund_id: Optional[str] = Field(None, title="Stripe Refund Id")
    delivered_date: Optional[int] = Field(None, title="Delivered Date")
    cancelled_date: Optional[int] = Field(None, title="Cancelled Date")
    refunded_date: Optional[int] = Field(None, title="Refunded Date")


class PresignedUrlResponse(BaseModel):
    upload_url: str = Field(..., title="Upload Url")
    artifact_id: str = Field(..., title="Artifact Id")


class ProcessPreorderResponse(BaseModel):
    status: str = Field(..., title="Status")
    checkout_session: Dict[str, Any] = Field(..., title="Checkout Session")


class ProductInfo(BaseModel):
    id: str = Field(..., title="Id")
    name: str = Field(..., title="Name")
    description: Optional[str] = Field(..., title="Description")
    images: List[str] = Field(..., title="Images")
    metadata: Dict[str, str] = Field(..., title="Metadata")
    active: bool = Field(..., title="Active")


class ProductResponse(BaseModel):
    id: str = Field(..., title="Id")
    name: str = Field(..., title="Name")
    description: Optional[str] = Field(..., title="Description")
    images: List[str] = Field(..., title="Images")
    metadata: Dict[str, str] = Field(..., title="Metadata")
    active: bool = Field(..., title="Active")


class PublicUserInfoResponseItem(BaseModel):
    id: str = Field(..., title="Id")
    email: str = Field(..., title="Email")
    username: str = Field(..., title="Username")
    permissions: Optional[List[Permission1]] = Field(None, title="Permissions")
    created_at: Optional[int] = Field(None, title="Created At")
    updated_at: Optional[int] = Field(None, title="Updated At")
    first_name: Optional[str] = Field(None, title="First Name")
    last_name: Optional[str] = Field(None, title="Last Name")
    name: Optional[str] = Field(None, title="Name")
    bio: Optional[str] = Field(None, title="Bio")


class PublicUsersInfoResponse(BaseModel):
    users: List[PublicUserInfoResponseItem] = Field(..., title="Users")


class Robot(BaseModel):
    id: str = Field(..., title="Id")
    user_id: str = Field(..., title="User Id")
    listing_id: str = Field(..., title="Listing Id")
    name: str = Field(..., title="Name")
    description: Optional[str] = Field(None, title="Description")
    created_at: int = Field(..., title="Created At")
    updated_at: int = Field(..., title="Updated At")
    order_id: Optional[str] = Field(None, title="Order Id")


class RobotURDFResponse(BaseModel):
    urdf_url: Optional[str] = Field(..., title="Urdf Url")


class SetContentManagerRequest(BaseModel):
    user_id: str = Field(..., title="User Id")
    is_content_manager: bool = Field(..., title="Is Content Manager")


class SetModeratorRequest(BaseModel):
    user_id: str = Field(..., title="User Id")
    is_mod: bool = Field(..., title="Is Mod")


class SetRequest(BaseModel):
    onshape_url: Optional[str] = Field(..., title="Onshape Url")


class ArtifactType(Enum):
    image = "image"


class ArtifactType1(Enum):
    kernel = "kernel"


class ArtifactType2(Enum):
    urdf = "urdf"
    mjcf = "mjcf"


class ArtifactType3(Enum):
    stl = "stl"
    obj = "obj"
    dae = "dae"
    ply = "ply"


class ArtifactType4(Enum):
    tgz = "tgz"
    zip = "zip"


class SingleArtifactResponse(BaseModel):
    artifact_id: str = Field(..., title="Artifact Id")
    listing_id: str = Field(..., title="Listing Id")
    username: str = Field(..., title="Username")
    slug: str = Field(..., title="Slug")
    name: str = Field(..., title="Name")
    artifact_type: Union[ArtifactType, ArtifactType1, ArtifactType2, ArtifactType3, ArtifactType4] = Field(
        ..., title="Artifact Type"
    )
    description: Optional[str] = Field(..., title="Description")
    timestamp: int = Field(..., title="Timestamp")
    urls: ArtifactUrls
    is_main: Optional[bool] = Field(False, title="Is Main")
    can_edit: Optional[bool] = Field(False, title="Can Edit")
    size: Optional[int] = Field(None, title="Size")


class SingleKRecResponse(BaseModel):
    id: str = Field(..., title="Id")
    name: str = Field(..., title="Name")
    created_at: int = Field(..., title="Created At")
    user_id: str = Field(..., title="User Id")
    robot_id: str = Field(..., title="Robot Id")
    type: Optional[str] = Field("KRec", title="Type")
    urls: Optional[KRecUrls] = None
    size: Optional[int] = Field(None, title="Size")


class SingleRobotResponse(BaseModel):
    robot_id: str = Field(..., title="Robot Id")
    user_id: str = Field(..., title="User Id")
    listing_id: str = Field(..., title="Listing Id")
    name: str = Field(..., title="Name")
    username: str = Field(..., title="Username")
    slug: str = Field(..., title="Slug")
    description: Optional[str] = Field(None, title="Description")
    order_id: Optional[str] = Field(None, title="Order Id")
    created_at: int = Field(..., title="Created At")


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
    onshape_url: Optional[str] = Field(None, title="Onshape Url")
    slug: Optional[str] = Field(None, title="Slug")
    stripe_product_id: Optional[str] = Field(None, title="Stripe Product Id")
    stripe_price_id: Optional[str] = Field(None, title="Stripe Price Id")
    stripe_deposit_price_id: Optional[str] = Field(None, title="Stripe Deposit Price Id")
    price_amount: Optional[int] = Field(None, title="Price Amount")
    preorder_release_date: Optional[int] = Field(None, title="Preorder Release Date")
    preorder_deposit_amount: Optional[int] = Field(None, title="Preorder Deposit Amount")
    stripe_preorder_deposit_id: Optional[str] = Field(None, title="Stripe Preorder Deposit Id")
    inventory_type: Optional[InventoryType] = Field(None, title="Inventory Type")
    inventory_quantity: Optional[int] = Field(None, title="Inventory Quantity")


class UpdateOrderAddressRequest(BaseModel):
    shipping_name: str = Field(..., title="Shipping Name")
    shipping_address_line1: str = Field(..., title="Shipping Address Line1")
    shipping_address_line2: Optional[str] = Field(..., title="Shipping Address Line2")
    shipping_city: str = Field(..., title="Shipping City")
    shipping_state: str = Field(..., title="Shipping State")
    shipping_postal_code: str = Field(..., title="Shipping Postal Code")
    shipping_country: str = Field(..., title="Shipping Country")


class UpdateOrderStatusRequest(BaseModel):
    status: Status = Field(..., title="Status")


class UpdateRobotRequest(BaseModel):
    name: Optional[str] = Field(None, title="Name")
    description: Optional[str] = Field(None, title="Description")
    order_id: Optional[str] = Field(None, title="Order Id")


class UpdateUserRequest(BaseModel):
    email: Optional[str] = Field(None, title="Email")
    password: Optional[str] = Field(None, title="Password")
    github_id: Optional[str] = Field(None, title="Github Id")
    google_id: Optional[str] = Field(None, title="Google Id")
    first_name: Optional[str] = Field(None, title="First Name")
    last_name: Optional[str] = Field(None, title="Last Name")
    name: Optional[str] = Field(None, title="Name")
    bio: Optional[str] = Field(None, title="Bio")


class UpdateUsernameRequest(BaseModel):
    new_username: str = Field(..., title="New Username")


class UploadArtifactResponse(BaseModel):
    artifacts: List[SingleArtifactResponse] = Field(..., title="Artifacts")


class UploadKRecRequest(BaseModel):
    name: str = Field(..., title="Name")
    robot_id: str = Field(..., title="Robot Id")
    description: Optional[str] = Field(None, title="Description")


class UserInfoResponseItem(BaseModel):
    id: str = Field(..., title="Id")
    email: str = Field(..., title="Email")


class UserSignup(BaseModel):
    signup_token_id: str = Field(..., title="Signup Token Id")
    email: str = Field(..., title="Email")
    password: str = Field(..., title="Password")


class UserStripeConnect(BaseModel):
    account_id: str = Field(..., title="Account Id")
    onboarding_completed: bool = Field(..., title="Onboarding Completed")


class ValidationError(BaseModel):
    loc: List[Union[str, int]] = Field(..., title="Location")
    msg: str = Field(..., title="Message")
    type: str = Field(..., title="Error Type")


class DumpListingsResponse(BaseModel):
    listings: List[Listing] = Field(..., title="Listings")


class GetListingResponse(BaseModel):
    id: str = Field(..., title="Id")
    name: str = Field(..., title="Name")
    description: Optional[str] = Field(..., title="Description")
    creator_id: Optional[str] = Field(..., title="Creator Id")
    creator_name: Optional[str] = Field(..., title="Creator Name")
    username: Optional[str] = Field(..., title="Username")
    slug: Optional[str] = Field(..., title="Slug")
    score: int = Field(..., title="Score")
    views: int = Field(..., title="Views")
    created_at: int = Field(..., title="Created At")
    artifacts: List[SingleArtifactResponse] = Field(..., title="Artifacts")
    can_edit: bool = Field(..., title="Can Edit")
    user_vote: Optional[bool] = Field(..., title="User Vote")
    onshape_url: Optional[str] = Field(..., title="Onshape Url")
    is_featured: bool = Field(..., title="Is Featured")
    currency: Optional[str] = Field(None, title="Currency")
    price_amount: Optional[int] = Field(None, title="Price Amount")
    stripe_product_id: Optional[str] = Field(None, title="Stripe Product Id")
    stripe_price_id: Optional[str] = Field(None, title="Stripe Price Id")
    preorder_deposit_amount: Optional[int] = Field(None, title="Preorder Deposit Amount")
    stripe_preorder_deposit_id: Optional[str] = Field(None, title="Stripe Preorder Deposit Id")
    preorder_release_date: Optional[int] = Field(None, title="Preorder Release Date")
    inventory_type: Optional[str] = Field(None, title="Inventory Type")
    inventory_quantity: Optional[int] = Field(None, title="Inventory Quantity")


class HTTPValidationError(BaseModel):
    detail: Optional[List[ValidationError]] = Field(None, title="Detail")


class ListArtifactsResponse(BaseModel):
    artifacts: List[SingleArtifactResponse] = Field(..., title="Artifacts")


class ListListingsResponse(BaseModel):
    listings: List[ListingInfo] = Field(..., title="Listings")
    has_next: Optional[bool] = Field(False, title="Has Next")


class ListingInfoResponse(BaseModel):
    id: str = Field(..., title="Id")
    name: str = Field(..., title="Name")
    slug: Optional[str] = Field(..., title="Slug")
    username: Optional[str] = Field(..., title="Username")
    description: Optional[str] = Field(..., title="Description")
    child_ids: List[str] = Field(..., title="Child Ids")
    artifacts: List[SingleArtifactResponse] = Field(..., title="Artifacts")
    onshape_url: Optional[str] = Field(..., title="Onshape Url")
    created_at: int = Field(..., title="Created At")
    views: int = Field(..., title="Views")
    score: int = Field(..., title="Score")
    user_vote: Optional[bool] = Field(..., title="User Vote")
    price_amount: Optional[int] = Field(..., title="Price Amount")
    currency: Optional[str] = Field(..., title="Currency")
    inventory_type: Optional[InventoryType] = Field(..., title="Inventory Type")
    inventory_quantity: Optional[int] = Field(..., title="Inventory Quantity")


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
    stripe_connect: Optional[UserStripeConnect]


class OrderWithProduct(BaseModel):
    order: Order
    product: Optional[ProductInfo]


class RobotListResponse(BaseModel):
    robots: List[SingleRobotResponse] = Field(..., title="Robots")


class UserPublic(BaseModel):
    id: str = Field(..., title="Id")
    email: str = Field(..., title="Email")
    username: str = Field(..., title="Username")
    permissions: Optional[List[Permission1]] = Field(None, title="Permissions")
    created_at: int = Field(..., title="Created At")
    updated_at: Optional[int] = Field(None, title="Updated At")
    first_name: Optional[str] = Field(None, title="First Name")
    last_name: Optional[str] = Field(None, title="Last Name")
    name: Optional[str] = Field(None, title="Name")
    bio: Optional[str] = Field(None, title="Bio")
    stripe_connect: Optional[UserStripeConnect] = None


class AdminOrdersResponse(BaseModel):
    orders: List[OrderWithProduct] = Field(..., title="Orders")


class GetBatchListingsResponse(BaseModel):
    listings: List[ListingInfoResponse] = Field(..., title="Listings")
