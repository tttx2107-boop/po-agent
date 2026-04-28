// ==============================================
// Fire Safety Annotation System
// Multimodal Knowledge Graph Annotation Tool
// ==============================================

// State Management
const state = {
    currentTool: 'select',
    zoom: 1,
    pan: { x: 0, y: 0 },
    isDrawing: false,
    isPanning: false,
    startPoint: null,
    currentImage: 0,
    selectedAnnotation: null,
    annotations: [],
    relationships: [],
    images: [],
    ocrResults: []
};

// Fire Safety Object Types with metadata
const OBJECT_TYPES = {
    fire_extinguisher: { name: '灭火器', icon: '🧯', color: '#e74c3c' },
    hydrant: { name: '消火栓', icon: '🚿', color: '#3498db' },
    sprinkler: { name: '喷淋头', icon: '💦', color: '#2ecc71' },
    fire_barrel: { name: '灭火桶', icon: '🪣', color: '#e67e22' },
    exit_sign: { name: '疏散标志', icon: '🚪', color: '#f1c40f' },
    emergency_exit: { name: '紧急出口', icon: '🚨', color: '#e74c3c' },
    fire_door: { name: '防火门', icon: '🔒', color: '#8e44ad' },
    escape_route: { name: '疏散路线', icon: '➡️', color: '#27ae60' },
    fire_detector: { name: '火灾探测器', icon: '📡', color: '#e74c3c' },
    smoke_detector: { name: '烟雾探测器', icon: '💨', color: '#95a5a6' },
    fire_alarm: { name: '火灾报警器', icon: '🔔', color: '#e74c3c' },
    fire_pump: { name: '消防泵', icon: '⚙️', color: '#34495e' },
    control_panel: { name: '控制面板', icon: '🎛️', color: '#3498db' },
    fire_hose: { name: '消防水带', icon: '🧯', color: '#e74c3c' }
};

// Relationship Types
const RELATIONSHIP_TYPES = {
    near: { name: '靠近', description: '空间距离近' },
    connected_to: { name: '连接', description: '物理连接' },
    part_of: { name: '组成', description: '整体与部分' },
    covers: { name: '覆盖', description: '覆盖区域' },
    leads_to: { name: '通向', description: '指向目的地' },
    monitors: { name: '监控', description: '监控关系' }
};

// Sample data for demonstration
const SAMPLE_IMAGES = [
    {
        id: 'img_001',
        url: 'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800',
        name: '消防栓检测点A',
        ocrResults: [
            { text: '消火栓', confidence: 0.95, bbox: [120, 80, 200, 120] },
            { text: '编号: FH-2024-001', confidence: 0.92, bbox: [100, 150, 250, 180] }
        ]
    },
    {
        id: 'img_002',
        url: 'https://images.unsplash.com/photo-1497366216548-37526070297c?w=800',
        name: '办公楼疏散通道',
        ocrResults: [
            { text: '紧急出口', confidence: 0.98, bbox: [300, 50, 500, 100] },
            { text: 'EXIT', confidence: 0.99, bbox: [320, 110, 480, 150] }
        ]
    },
    {
        id: 'img_003',
        url: 'https://images.unsplash.com/photo-1584634731339-252e581abfc5?w=800',
        name: '灭火器检查',
        ocrResults: [
            { text: '灭火器', confidence: 0.94, bbox: [150, 100, 280, 200] },
            { text: '下次检验: 2025-06', confidence: 0.88, bbox: [140, 210, 300, 240] }
        ]
    }
];

// DOM Elements
let annotationCanvas, interactionCanvas;
let annotationCtx, interactionCtx;
let canvasContainer;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initCanvas();
    initEventListeners();
    loadSampleData();
    loadFromLocalStorage();
    updateUI();
});

function initCanvas() {
    annotationCanvas = document.getElementById('annotationCanvas');
    interactionCanvas = document.getElementById('interactionCanvas');
    canvasContainer = document.getElementById('canvasContainer');
    
    annotationCtx = annotationCanvas.getContext('2d');
    interactionCtx = interactionCanvas.getContext('2d');
    
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);
}

function resizeCanvas() {
    const container = canvasContainer;
    const width = container.clientWidth;
    const height = container.clientHeight;
    
    annotationCanvas.width = width;
    annotationCanvas.height = height;
    interactionCanvas.width = width;
    interactionCanvas.height = height;
    
    annotationCanvas.style.width = width + 'px';
    annotationCanvas.style.height = height + 'px';
    interactionCanvas.style.width = width + 'px';
    interactionCanvas.style.height = height + 'px';
    
    drawImage();
}

function initEventListeners() {
    // Canvas events
    interactionCanvas.addEventListener('mousedown', handleMouseDown);
    interactionCanvas.addEventListener('mousemove', handleMouseMove);
    interactionCanvas.addEventListener('mouseup', handleMouseUp);
    interactionCanvas.addEventListener('wheel', handleWheel);
    
    // Keyboard shortcuts
    document.addEventListener('keydown', handleKeyDown);
    
    // Object type change
    document.getElementById('objectType').addEventListener('change', handleTypeChange);
}

function loadSampleData() {
    state.images = SAMPLE_IMAGES;
    state.currentImage = 0;
    updateImageCounter();
}

function handleMouseDown(e) {
    const point = getCanvasPoint(e);
    state.startPoint = point;
    
    if (state.currentTool === 'box') {
        state.isDrawing = true;
        canvasContainer.classList.add('drawing');
    } else if (state.currentTool === 'pan') {
        state.isPanning = true;
        canvasContainer.classList.add('panning');
    } else if (state.currentTool === 'select') {
        handleSelection(point);
    }
}

function handleMouseMove(e) {
    const point = getCanvasPoint(e);
    
    if (state.isDrawing && state.startPoint) {
        drawInteraction(point);
    } else if (state.isPanning) {
        const dx = e.movementX;
        const dy = e.movementY;
        state.pan.x += dx;
        state.pan.y += dy;
        drawImage();
    }
}

function handleMouseUp(e) {
    const point = getCanvasPoint(e);
    
    if (state.isDrawing && state.startPoint) {
        const bbox = calculateBBox(state.startPoint, point);
        if (bbox.width > 10 && bbox.height > 10) {
            createAnnotation(bbox);
        }
    }
    
    state.isDrawing = false;
    state.isPanning = false;
    state.startPoint = null;
    canvasContainer.classList.remove('drawing', 'panning');
    clearInteractionCanvas();
}

function handleWheel(e) {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.1 : 0.1;
    zoom(delta);
}

function handleKeyDown(e) {
    switch(e.key) {
        case 'Delete':
        case 'Backspace':
            if (state.selectedAnnotation) {
                deleteAnnotation(state.selectedAnnotation.id);
            }
            break;
        case 'Escape':
            clearSelection();
            break;
        case 's':
            if (e.ctrlKey || e.metaKey) {
                e.preventDefault();
                saveAnnotation();
            }
            break;
    }
}

function getCanvasPoint(e) {
    const rect = interactionCanvas.getBoundingClientRect();
    return {
        x: (e.clientX - rect.left - state.pan.x) / state.zoom,
        y: (e.clientY - rect.top - state.pan.y) / state.zoom
    };
}

function calculateBBox(p1, p2) {
    return {
        x: Math.min(p1.x, p2.x),
        y: Math.min(p1.y, p2.y),
        width: Math.abs(p2.x - p1.x),
        height: Math.abs(p2.y - p1.y)
    };
}

// Tool Management
function setTool(tool) {
    state.currentTool = tool;
    document.querySelectorAll('.tool-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.getElementById(tool + 'Tool')?.classList.add('active');
}

// Zoom Controls
function zoom(delta) {
    state.zoom = Math.max(0.1, Math.min(5, state.zoom + delta));
    document.getElementById('zoomLevel').textContent = Math.round(state.zoom * 100) + '%';
    drawImage();
}

function zoomIn() {
    zoom(0.2);
}

function zoomOut() {
    zoom(-0.2);
}

function resetZoom() {
    state.zoom = 1;
    state.pan = { x: 0, y: 0 };
    document.getElementById('zoomLevel').textContent = '100%';
    drawImage();
}

// Image Drawing
function drawImage() {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
        const canvas = annotationCanvas;
        const ctx = annotationCtx;
        
        // Clear canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Calculate scaled dimensions
        const imgWidth = img.width * state.zoom;
        const imgHeight = img.height * state.zoom;
        
        // Center offset
        const offsetX = (canvas.width - imgWidth) / 2 + state.pan.x;
        const offsetY = (canvas.height - imgHeight) / 2 + state.pan.y;
        
        // Draw image
        ctx.drawImage(img, offsetX, offsetY, imgWidth, imgHeight);
        
        // Store image info for coordinate conversion
        state.imageInfo = {
            img,
            offsetX,
            offsetY,
            imgWidth,
            imgHeight,
            naturalWidth: img.width,
            naturalHeight: img.height
        };
        
        // Draw existing annotations
        drawAnnotations();
    };
    img.src = state.images[state.currentImage]?.url || '';
}

function drawAnnotations() {
    const ctx = interactionCtx;
    ctx.clearRect(0, 0, interactionCanvas.width, interactionCanvas.height);
    
    state.annotations.forEach(ann => {
        if (ann.imageId === state.images[state.currentImage]?.id) {
            drawBoundingBox(ann);
        }
    });
    
    // Draw selected annotation highlight
    if (state.selectedAnnotation) {
        const selected = state.annotations.find(a => a.id === state.selectedAnnotation);
        if (selected) {
            drawBoundingBox(selected, true);
        }
    }
}

function drawBoundingBox(annotation, isSelected = false) {
    if (!state.imageInfo) return;
    
    const { offsetX, offsetY, imgWidth, imgHeight, naturalWidth, naturalHeight } = state.imageInfo;
    
    // Scale bbox to current view
    const scaleX = imgWidth / naturalWidth;
    const scaleY = imgHeight / naturalHeight;
    
    const x = offsetX + annotation.bbox.x * scaleX;
    const y = offsetY + annotation.bbox.y * scaleY;
    const w = annotation.bbox.width * scaleX;
    const h = annotation.bbox.height * scaleY;
    
    const ctx = interactionCtx;
    const typeInfo = OBJECT_TYPES[annotation.type] || { color: '#ffffff' };
    
    // Draw box
    ctx.strokeStyle = isSelected ? '#ffff00' : typeInfo.color;
    ctx.lineWidth = isSelected ? 3 : 2;
    ctx.strokeRect(x, y, w, h);
    
    // Draw fill
    ctx.fillStyle = isSelected ? 'rgba(255, 255, 0, 0.2)' : hexToRgba(typeInfo.color, 0.2);
    ctx.fillRect(x, y, w, h);
    
    // Draw label
    const label = typeInfo.icon + ' ' + typeInfo.name;
    ctx.font = '14px sans-serif';
    const metrics = ctx.measureText(label);
    const labelX = x;
    const labelY = y - 5;
    
    ctx.fillStyle = typeInfo.color;
    ctx.fillRect(labelX, labelY - 14, metrics.width + 8, 18);
    ctx.fillStyle = 'white';
    ctx.fillText(label, labelX + 4, labelY);
}

function hexToRgba(hex, alpha) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function drawInteraction(currentPoint) {
    clearInteractionCanvas();
    
    if (!state.startPoint || !currentPoint) return;
    
    const ctx = interactionCtx;
    const bbox = calculateBBox(state.startPoint, currentPoint);
    
    // Scale to view
    if (state.imageInfo) {
        const { offsetX, offsetY, imgWidth, imgHeight, naturalWidth, naturalHeight } = state.imageInfo;
        const scaleX = imgWidth / naturalWidth;
        const scaleY = imgHeight / naturalHeight;
        
        bbox.x = offsetX + bbox.x;
        bbox.y = offsetY + bbox.y;
        bbox.width *= scaleX;
        bbox.height *= scaleY;
    }
    
    ctx.strokeStyle = '#e74c3c';
    ctx.lineWidth = 2;
    ctx.setLineDash([5, 5]);
    ctx.strokeRect(bbox.x, bbox.y, bbox.width, bbox.height);
    ctx.fillStyle = 'rgba(231, 76, 60, 0.2)';
    ctx.fillRect(bbox.x, bbox.y, bbox.width, bbox.height);
}

function clearInteractionCanvas() {
    interactionCtx.clearRect(0, 0, interactionCanvas.width, interactionCanvas.height);
}

// Selection
function handleSelection(point) {
    if (!state.imageInfo) return;
    
    const { offsetX, offsetY, imgWidth, imgHeight, naturalWidth, naturalHeight } = state.imageInfo;
    const scaleX = imgWidth / naturalWidth;
    const scaleY = imgHeight / naturalHeight;
    
    // Convert to image coordinates
    const imgX = (point.x - offsetX) / scaleX;
    const imgY = (point.y - offsetY) / scaleY;
    
    // Find annotation at point
    const clicked = state.annotations.find(ann => {
        if (ann.imageId !== state.images[state.currentImage]?.id) return false;
        const b = ann.bbox;
        return imgX >= b.x && imgX <= b.x + b.width &&
               imgY >= b.y && imgY <= b.y + b.height;
    });
    
    if (clicked) {
        selectAnnotation(clicked.id);
    } else {
        clearSelection();
    }
}

function selectAnnotation(id) {
    state.selectedAnnotation = id;
    populateForm(id);
    updateAnnotationList();
    drawAnnotations();
}

function clearSelection() {
    state.selectedAnnotation = null;
    clearForm();
    updateAnnotationList();
    drawAnnotations();
}

// Annotation CRUD
function createAnnotation(bbox) {
    if (!state.imageInfo) return;
    
    const { naturalWidth, naturalHeight } = state.imageInfo;
    
    // Convert view bbox to image bbox
    const { offsetX, offsetY, imgWidth, imgHeight } = state.imageInfo;
    const scaleX = naturalWidth / imgWidth;
    const scaleY = naturalHeight / imgHeight;
    
    const imageBbox = {
        x: (bbox.x - offsetX) * scaleX,
        y: (bbox.y - offsetY) * scaleY,
        width: bbox.width * scaleX,
        height: bbox.height * scaleY
    };
    
    const annotation = {
        id: generateId(),
        imageId: state.images[state.currentImage].id,
        type: '',
        bbox: imageBbox,
        attributes: {
            status: 'normal',
            visibility: 'visible',
            color: '',
            id: ''
        },
        description: '',
        customAttributes: {},
        verified: false,
        createdAt: new Date().toISOString()
    };
    
    state.annotations.push(annotation);
    state.selectedAnnotation = annotation.id;
    
    updateUI();
    drawAnnotations();
    populateForm(annotation.id);
    showToast('边界框已创建，请填写标注信息', 'success');
}

function updateAnnotation(id, updates) {
    const index = state.annotations.findIndex(a => a.id === id);
    if (index !== -1) {
        state.annotations[index] = { ...state.annotations[index], ...updates };
        saveToLocalStorage();
        updateAnnotationList();
        drawAnnotations();
    }
}

function deleteAnnotation(id) {
    showModal('确定要删除此标注吗？', () => {
        state.annotations = state.annotations.filter(a => a.id !== id);
        state.relationships = state.relationships.filter(
            r => r.source !== id && r.target !== id
        );
        if (state.selectedAnnotation === id) {
            clearSelection();
        }
        updateUI();
        showToast('标注已删除', 'warning');
    });
}

// Form Handling
function populateForm(id) {
    const annotation = state.annotations.find(a => a.id === id);
    if (!annotation) return;
    
    document.getElementById('objectType').value = annotation.type || '';
    document.getElementById('attrStatus').value = annotation.attributes?.status || 'normal';
    document.getElementById('attrVisibility').value = annotation.attributes?.visibility || 'visible';
    document.getElementById('attrColor').value = annotation.attributes?.color || '';
    document.getElementById('attrId').value = annotation.attributes?.id || '';
    document.getElementById('objectDescription').value = annotation.description || '';
    
    // Populate custom attributes
    const customAttrsDiv = document.getElementById('customAttrs');
    customAttrsDiv.innerHTML = '';
    const customAttrs = annotation.customAttributes || {};
    Object.entries(customAttrs).forEach(([key, value]) => {
        addCustomAttrRow(key, value);
    });
    if (Object.keys(customAttrs).length === 0) {
        addCustomAttrRow();
    }
}

function addCustomAttrRow(key = '', value = '') {
    const div = document.createElement('div');
    div.className = 'custom-attr-row';
    div.innerHTML = `
        <input type="text" class="form-control attr-key" placeholder="属性名" value="${key}">
        <input type="text" class="form-control attr-value" placeholder="属性值" value="${value}">
        <button class="btn-icon" onclick="removeCustomAttr(this)">✕</button>
    `;
    document.getElementById('customAttrs').appendChild(div);
}

function addCustomAttr() {
    addCustomAttrRow();
}

function removeCustomAttr(btn) {
    const row = btn.parentElement;
    const container = document.getElementById('customAttrs');
    if (container.children.length > 1) {
        row.remove();
    } else {
        row.querySelectorAll('input').forEach(input => input.value = '');
    }
}

function clearForm() {
    document.getElementById('objectType').value = '';
    document.getElementById('attrStatus').value = 'normal';
    document.getElementById('attrVisibility').value = 'visible';
    document.getElementById('attrColor').value = '';
    document.getElementById('attrId').value = '';
    document.getElementById('objectDescription').value = '';
    
    const customAttrsDiv = document.getElementById('customAttrs');
    customAttrsDiv.innerHTML = '';
    addCustomAttrRow();
}

function handleTypeChange() {
    if (state.selectedAnnotation) {
        saveAnnotation();
    }
}

function saveAnnotation() {
    if (!state.selectedAnnotation) {
        showToast('请先选择或创建标注', 'warning');
        return;
    }
    
    const customAttributes = {};
    document.querySelectorAll('.custom-attr-row').forEach(row => {
        const key = row.querySelector('.attr-key').value.trim();
        const value = row.querySelector('.attr-value').value.trim();
        if (key) {
            customAttributes[key] = value;
        }
    });
    
    const updates = {
        type: document.getElementById('objectType').value,
        attributes: {
            status: document.getElementById('attrStatus').value,
            visibility: document.getElementById('attrVisibility').value,
            color: document.getElementById('attrColor').value,
            id: document.getElementById('attrId').value
        },
        description: document.getElementById('objectDescription').value,
        customAttributes
    };
    
    updateAnnotation(state.selectedAnnotation, updates);
    updateSaveStatus('saving');
    setTimeout(() => updateSaveStatus('saved'), 500);
    showToast('标注已保存', 'success');
}

function verifyAnnotation() {
    if (!state.selectedAnnotation) {
        showToast('请先选择标注', 'warning');
        return;
    }
    
    const annotation = state.annotations.find(a => a.id === state.selectedAnnotation);
    if (!annotation.type) {
        showToast('请先选择对象类型', 'error');
        return;
    }
    
    updateAnnotation(state.selectedAnnotation, { verified: true });
    showToast('标注已验证 ✓', 'success');
}

// Relationships
function addRelationship() {
    const source = document.getElementById('relSource').value;
    const type = document.getElementById('relType').value;
    const target = document.getElementById('relTarget').value;
    
    if (!source || !type || !target) {
        showToast('请完整填写关系信息', 'warning');
        return;
    }
    
    if (source === target) {
        showToast('源对象和目标对象不能相同', 'error');
        return;
    }
    
    // Check if relationship exists
    const exists = state.relationships.some(
        r => r.source === source && r.target === target && r.type === type
    );
    
    if (exists) {
        showToast('此关系已存在', 'warning');
        return;
    }
    
    state.relationships.push({
        id: generateId(),
        source,
        type,
        target,
        createdAt: new Date().toISOString()
    });
    
    updateRelationshipList();
    saveToLocalStorage();
    showToast('关系已添加', 'success');
}

function deleteRelationship(id) {
    state.relationships = state.relationships.filter(r => r.id !== id);
    updateRelationshipList();
    saveToLocalStorage();
}

// Image Navigation
function prevImage() {
    if (state.currentImage > 0) {
        state.currentImage--;
        clearSelection();
        resetZoom();
        updateImageCounter();
        loadOcrResults();
        drawImage();
    }
}

function nextImage() {
    if (state.currentImage < state.images.length - 1) {
        state.currentImage++;
        clearSelection();
        resetZoom();
        updateImageCounter();
        loadOcrResults();
        drawImage();
    }
}

function updateImageCounter() {
    const counter = document.getElementById('imageCounter');
    counter.textContent = `${state.currentImage + 1} / ${state.images.length}`;
}

function loadOcrResults() {
    const ocrContent = document.getElementById('ocrContent');
    const image = state.images[state.currentImage];
    
    if (!image || !image.ocrResults || image.ocrResults.length === 0) {
        ocrContent.innerHTML = '<p class="ocr-placeholder">此图片暂无OCR识别结果</p>';
        return;
    }
    
    ocrContent.innerHTML = image.ocrResults.map(ocr => `
        <div class="ocr-text">
            <strong>${ocr.text}</strong>
            <span style="color: #27ae60; margin-left: 8px;">置信度: ${(ocr.confidence * 100).toFixed(1)}%</span>
        </div>
    `).join('');
}

function toggleOcrPanel() {
    document.getElementById('ocrPanel').classList.toggle('collapsed');
}

// UI Updates
function updateUI() {
    updateAnnotationList();
    updateRelationshipList();
    updateRelationshipSelects();
    loadOcrResults();
}

function updateAnnotationList() {
    const list = document.getElementById('annotationList');
    const currentImageId = state.images[state.currentImage]?.id;
    
    const annotations = state.annotations.filter(a => a.imageId === currentImageId);
    
    if (annotations.length === 0) {
        list.innerHTML = '<p class="empty-state">暂无标注</p>';
        return;
    }
    
    list.innerHTML = annotations.map(ann => {
        const typeInfo = OBJECT_TYPES[ann.type] || { name: '未分类', icon: '❓', color: '#95a5a6' };
        const isSelected = state.selectedAnnotation === ann.id;
        const statusClass = ann.verified ? '✓ 已验证' : '待验证';
        
        return `
            <div class="annotation-item ${isSelected ? 'selected' : ''}" onclick="selectAnnotation('${ann.id}')">
                <div class="annotation-header">
                    <span class="annotation-type">${typeInfo.icon} ${typeInfo.name}</span>
                    <span class="annotation-attrs">${statusClass}</span>
                </div>
                <div class="annotation-attrs">
                    状态: ${ann.attributes?.status || '-'} | 
                    可见性: ${ann.attributes?.visibility || '-'}
                </div>
                <div class="annotation-actions">
                    <button class="btn-edit" onclick="event.stopPropagation(); selectAnnotation('${ann.id}')">编辑</button>
                    <button class="btn-delete" onclick="event.stopPropagation(); deleteAnnotation('${ann.id}')">删除</button>
                </div>
            </div>
        `;
    }).join('');
}

function updateRelationshipList() {
    const list = document.getElementById('relationshipList');
    
    if (state.relationships.length === 0) {
        list.innerHTML = '<p class="empty-state">暂无关系标注</p>';
        return;
    }
    
    list.innerHTML = state.relationships.map(rel => {
        const sourceAnn = state.annotations.find(a => a.id === rel.source);
        const targetAnn = state.annotations.find(a => a.id === rel.target);
        const relType = RELATIONSHIP_TYPES[rel.type] || { name: rel.type };
        
        const sourceName = sourceAnn ? (OBJECT_TYPES[sourceAnn.type]?.name || '未知') : '已删除';
        const targetName = targetAnn ? (OBJECT_TYPES[targetAnn.type]?.name || '未知') : '已删除';
        
        return `
            <div class="relationship-item">
                <div class="relationship-text">
                    ${sourceName} <span class="rel-arrow">→</span> ${relType.name} <span class="rel-arrow">→</span> ${targetName}
                </div>
                <div class="annotation-actions" style="justify-content: center; margin-top: 8px;">
                    <button class="btn-delete" onclick="deleteRelationship('${rel.id}')">删除</button>
                </div>
            </div>
        `;
    }).join('');
}

function updateRelationshipSelects() {
    const sourceSelect = document.getElementById('relSource');
    const targetSelect = document.getElementById('relTarget');
    const currentImageId = state.images[state.currentImage]?.id;
    
    const annotations = state.annotations.filter(a => a.imageId === currentImageId);
    
    const options = '<option value="">-- 选择 --</option>' + 
        annotations.map(ann => {
            const typeInfo = OBJECT_TYPES[ann.type] || { name: '未分类', icon: '❓' };
            return `<option value="${ann.id}">${typeInfo.icon} ${typeInfo.name}</option>`;
        }).join('');
    
    sourceSelect.innerHTML = options;
    targetSelect.innerHTML = options;
}

// Export & Submit
function exportAnnotations() {
    const data = {
        annotations: state.annotations,
        relationships: state.relationships,
        metadata: {
            exportedAt: new Date().toISOString(),
            imageCount: state.images.length,
            annotationCount: state.annotations.length
        }
    };
    
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `annotations_${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    
    showToast('标注已导出', 'success');
}

function submitAnnotations() {
    const unverified = state.annotations.filter(a => !a.verified && a.type);
    const untyped = state.annotations.filter(a => !a.type);
    
    if (untyped.length > 0) {
        showToast(`还有 ${untyped.length} 个标注未选择类型`, 'warning');
        return;
    }
    
    if (unverified.length > 0) {
        showToast(`还有 ${unverified.length} 个标注未验证`, 'warning');
        return;
    }
    
    showModal('确定要提交所有标注吗？提交后将无法修改。', () => {
        state.annotations.forEach(a => a.submitted = true);
        saveToLocalStorage();
        showToast('标注已提交审核！', 'success');
    });
}

// Local Storage
function saveToLocalStorage() {
    const data = {
        annotations: state.annotations,
        relationships: state.relationships,
        currentImage: state.currentImage
    };
    localStorage.setItem('annotation_draft', JSON.stringify(data));
    updateSaveStatus('saved');
}

function loadFromLocalStorage() {
    const saved = localStorage.getItem('annotation_draft');
    if (saved) {
        try {
            const data = JSON.parse(saved);
            state.annotations = data.annotations || [];
            state.relationships = data.relationships || [];
            state.currentImage = data.currentImage || 0;
        } catch (e) {
            console.error('Failed to load from localStorage', e);
        }
    }
}

function updateSaveStatus(status) {
    const el = document.getElementById('saveStatus');
    el.className = 'status-indicator ' + status;
    el.textContent = status === 'saving' ? '保存中...' : '已保存';
}

// Modal & Toast
function showModal(message, onConfirm) {
    document.getElementById('modalMessage').textContent = message;
    document.getElementById('confirmModal').classList.add('show');
    window.confirmAction = onConfirm;
}

function closeModal() {
    document.getElementById('confirmModal').classList.remove('show');
}

function confirmAction() {
    if (window.confirmAction) {
        window.confirmAction();
    }
    closeModal();
}

function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toastMessage');
    
    toast.className = 'toast ' + type;
    toastMessage.textContent = message;
    toast.classList.add('show');
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// Utilities
function generateId() {
    return 'ann_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

// Initialize OCR panel
loadOcrResults();
