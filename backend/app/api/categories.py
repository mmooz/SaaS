"""分类管理 API：树形列表、新增、更新、删除。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_manager_user, get_store_id, get_tenant_id
from app.models import Category, Product, User
from app.schemas.category_create import CategoryCreate
from app.schemas.category_out import CategoryOut
from app.schemas.category_update import CategoryUpdate

# 分类路由
router = APIRouter(prefix="/api/categories", tags=["分类管理"])


def build_tree(categories: list[Category]) -> list[CategoryOut]:
    """将扁平分类列表构建为树形结构（一级为根，二级挂子节点）。

    注意：显式构造节点并传入空 children，避免 model_validate 通过 ORM 的
    children relationship 自动递归填充，导致与手动组装产生重复。
    """
    node_map: dict[int, CategoryOut] = {
        c.id: CategoryOut(
            id=c.id,
            name=c.name,
            parent_id=c.parent_id,
            sort=c.sort,
            enabled=c.enabled,
            store_id=c.store_id,
            created_at=c.created_at,
            children=[],
        )
        for c in categories
    }
    tree: list[CategoryOut] = []
    for cat in categories:
        node = node_map[cat.id]
        if cat.parent_id and cat.parent_id in node_map:
            parent = node_map[cat.parent_id]
            parent.children.append(node)
        else:
            tree.append(node)
    return tree


@router.get("/tree", response_model=list[CategoryOut])
def get_category_tree(
    db: Session = Depends(get_db), store_id: int = Depends(get_store_id)
):
    """获取当前门店全部分类的树形结构。"""
    categories = db.scalars(
        select(Category)
        .where(Category.store_id == store_id)
        .order_by(Category.sort, Category.id)
    ).all()
    return build_tree(list(categories))


@router.post("", response_model=CategoryOut, status_code=201)
def create_category(
    data: CategoryCreate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_tenant_id),
    store_id: int = Depends(get_store_id),
    _user: User = Depends(get_manager_user),
):
    """新增分类。"""
    # 校验上级分类存在且属于当前门店
    if data.parent_id:
        parent = db.scalar(
            select(Category).where(
                Category.id == data.parent_id, Category.store_id == store_id
            )
        )
        if not parent:
            raise HTTPException(status_code=404, detail="上级分类不存在")
    category = Category(
        **data.model_dump(exclude={"store_id"}),
        tenant_id=tenant_id,
        store_id=store_id,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.put("/{category_id}", response_model=CategoryOut)
def update_category(
    category_id: int,
    data: CategoryUpdate,
    db: Session = Depends(get_db),
    store_id: int = Depends(get_store_id),
    _user: User = Depends(get_manager_user),
):
    """更新分类（仅更新传入字段）。"""
    category = db.scalar(
        select(Category).where(Category.id == category_id, Category.store_id == store_id)
    )
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(category, key, value)
    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}")
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    store_id: int = Depends(get_store_id),
    _user: User = Depends(get_manager_user),
):
    """删除分类（存在子分类或商品时禁止删除）。"""
    category = db.scalar(
        select(Category).where(Category.id == category_id, Category.store_id == store_id)
    )
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")
    child_count = db.scalar(
        select(Category.id).where(
            Category.parent_id == category_id, Category.store_id == store_id
        )
    )
    if child_count:
        raise HTTPException(status_code=409, detail="该分类存在子分类，请先处理子分类")
    product_count = db.scalar(
        select(Product.id).where(
            Product.category_id == category_id,
            Product.store_id == store_id,
            Product.deleted.is_(False),
        )
    )
    if product_count:
        raise HTTPException(status_code=409, detail="该分类下存在商品，无法删除")
    db.delete(category)
    db.commit()
    return {"message": "删除成功"}
