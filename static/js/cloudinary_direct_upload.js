(function () {
  function getCookie(name) {
    const match = document.cookie.match(new RegExp("(^|;\\s*)" + name + "=([^;]*)"));
    return match ? decodeURIComponent(match[2]) : "";
  }

  function ensureUi(input) {
    const wrapper = input.closest(".form-row, .fieldBox, .flex, .grid, div") || input.parentElement;
    let container = input.parentElement && input.parentElement.querySelector("[data-cloudinary-ui]");
    if (container) return container;

    container = document.createElement("div");
    container.setAttribute("data-cloudinary-ui", "1");
    container.style.marginTop = "12px";
    container.style.display = "grid";
    container.style.gap = "8px";

    const preview = document.createElement("div");
    preview.setAttribute("data-cloudinary-preview", "1");
    preview.style.display = "none";
    preview.style.borderRadius = "16px";
    preview.style.padding = "12px";
    preview.style.background = "rgba(0,0,0,0.2)";
    preview.style.border = "1px solid rgba(255,255,255,0.1)";
    container.appendChild(preview);

    const status = document.createElement("div");
    status.setAttribute("data-cloudinary-status", "1");
    status.style.fontSize = "12px";
    status.style.color = "rgba(255,255,255,0.65)";
    container.appendChild(status);

    const progressOuter = document.createElement("div");
    progressOuter.style.height = "8px";
    progressOuter.style.overflow = "hidden";
    progressOuter.style.borderRadius = "999px";
    progressOuter.style.background = "rgba(255,255,255,0.12)";
    progressOuter.innerHTML = '<div data-cloudinary-progress style="height:100%;width:0%;border-radius:999px;background:#27c27d;transition:width 150ms ease;"></div>';
    container.appendChild(progressOuter);

    if (wrapper && wrapper.insertBefore) {
      wrapper.insertBefore(container, input.nextSibling);
    } else if (input.parentElement) {
      input.parentElement.appendChild(container);
    }

    return container;
  }

  function getFieldNodes(input) {
    const ui = ensureUi(input);
    return {
      ui,
      status: ui.querySelector("[data-cloudinary-status]"),
      preview: ui.querySelector("[data-cloudinary-preview]"),
      progress: ui.querySelector("[data-cloudinary-progress]"),
    };
  }

  function setHiddenValue(prefix, suffix, value) {
    const el = document.getElementById(`id_${prefix}_${suffix}`);
    if (el) el.value = value || "";
  }

  function clearProgress(nodes) {
    if (nodes.progress) nodes.progress.style.width = "0%";
  }

  function renderPreview(input, file, nodes) {
    if (!nodes.preview || !file) return;

    nodes.preview.style.display = "block";
    nodes.preview.innerHTML = "";

    const title = document.createElement("div");
    title.style.fontSize = "12px";
    title.style.fontWeight = "700";
    title.style.color = "rgba(255,255,255,0.9)";
    title.textContent = "Selected file";

    const meta = document.createElement("div");
    meta.style.marginTop = "4px";
    meta.style.fontSize = "11px";
    meta.style.color = "rgba(255,255,255,0.6)";
    meta.textContent = `${file.name} · ${(file.size / (1024 * 1024)).toFixed(1)} MB`;

    nodes.preview.appendChild(title);
    nodes.preview.appendChild(meta);

    if (file.type.startsWith("image/")) {
      const img = document.createElement("img");
      img.style.marginTop = "12px";
      img.style.maxHeight = "192px";
      img.style.width = "100%";
      img.style.borderRadius = "12px";
      img.style.objectFit = "contain";
      img.alt = file.name;
      img.src = URL.createObjectURL(file);
      nodes.preview.appendChild(img);
    } else if (file.type.startsWith("video/")) {
      const video = document.createElement("video");
      video.style.marginTop = "12px";
      video.style.maxHeight = "192px";
      video.style.width = "100%";
      video.style.borderRadius = "12px";
      video.controls = true;
      video.playsInline = true;
      video.src = URL.createObjectURL(file);
      nodes.preview.appendChild(video);
    } else if (file.type.startsWith("audio/")) {
      const audio = document.createElement("audio");
      audio.style.marginTop = "12px";
      audio.style.width = "100%";
      audio.controls = true;
      audio.src = URL.createObjectURL(file);
      nodes.preview.appendChild(audio);
    } else {
      const note = document.createElement("div");
      note.style.marginTop = "12px";
      note.style.borderRadius = "12px";
      note.style.padding = "10px 12px";
      note.style.background = "rgba(255,255,255,0.05)";
      note.style.fontSize = "12px";
      note.style.color = "rgba(255,255,255,0.72)";
      note.textContent = "Preview unavailable for this file type.";
      nodes.preview.appendChild(note);
    }
  }

  async function requestSignature(signatureUrl, payload) {
    const response = await fetch(signatureUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      body: JSON.stringify(payload),
      credentials: "same-origin",
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Unable to sign upload request.");
    }
    return data;
  }

  function uploadWithProgress(url, formData, nodes) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", url);
      xhr.upload.onprogress = function (event) {
        if (!event.lengthComputable || !nodes.progress || !nodes.status) return;
        const pct = Math.max(1, Math.round((event.loaded / event.total) * 100));
        nodes.progress.style.width = `${pct}%`;
        nodes.status.textContent = `Uploading... ${pct}%`;
      };
      xhr.onload = function () {
        try {
          const data = JSON.parse(xhr.responseText || "{}");
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve(data);
            return;
          }
          reject(new Error(data.error && data.error.message ? data.error.message : "Cloudinary upload failed."));
        } catch (error) {
          reject(error);
        }
      };
      xhr.onerror = function () {
        reject(new Error("Cloudinary upload failed."));
      };
      xhr.send(formData);
    });
  }

  async function uploadFile(input, file) {
    const form = input.closest("form");
    const prefix = input.dataset.cloudinaryHiddenPrefix;
    const folder = input.dataset.cloudinaryFolder || "";
    const type = input.dataset.cloudinaryType || "upload";
    const resourceType = input.dataset.cloudinaryResourceType || "auto";
    const signatureUrl = input.dataset.cloudinarySignatureUrl || "";
    const unsignedPreset = input.dataset.cloudinaryUnsignedPreset || "";
    const uploadMode = input.dataset.cloudinaryUploadMode || (signatureUrl ? "signed" : "unsigned");
    const nodes = getFieldNodes(input);
    const submitButtons = form ? form.querySelectorAll("button[type='submit'], input[type='submit']") : [];

    submitButtons.forEach((button) => {
      button.disabled = true;
    });
    if (nodes.status) nodes.status.textContent = "Preparing upload...";
    clearProgress(nodes);
    renderPreview(input, file, nodes);

    try {
      let uploadUrl = `https://api.cloudinary.com/v1_1/${window.__cloudinaryUploadConfig?.cloudName || ""}/${resourceType}/upload`;
      const formData = new FormData();
      formData.append("file", file);
      formData.append("folder", folder);

      if (uploadMode === "signed") {
        const signed = await requestSignature(signatureUrl, {
          folder,
          type,
          resource_type: resourceType,
        });
        uploadUrl = `https://api.cloudinary.com/v1_1/${signed.cloudName}/${resourceType}/upload`;
        formData.append("api_key", signed.apiKey);
        formData.append("timestamp", signed.timestamp);
        formData.append("signature", signed.signature);
        formData.append("resource_type", resourceType);
        formData.append("type", type);
      } else {
        if (!unsignedPreset) {
          throw new Error("Missing unsigned upload preset.");
        }
        formData.append("upload_preset", unsignedPreset);
        formData.append("type", type);
        formData.append("resource_type", resourceType);
      }

      if (nodes.status) nodes.status.textContent = "Uploading to Cloudinary...";
      const result = await uploadWithProgress(uploadUrl, formData, nodes);
      setHiddenValue(prefix, "id", result.public_id || "");
      setHiddenValue(prefix, "format", result.format || "");
      setHiddenValue(prefix, "delivery", type || "upload");
      setHiddenValue(prefix, "resource_type", result.resource_type || resourceType || "auto");
      if (nodes.status) nodes.status.textContent = "Upload complete.";
      if (nodes.progress) nodes.progress.style.width = "100%";
      input.value = "";
    } catch (error) {
      console.error(error);
      if (nodes.status) nodes.status.textContent = error && error.message ? error.message : "Cloudinary upload failed.";
      clearProgress(nodes);
    } finally {
      submitButtons.forEach((button) => {
        button.disabled = false;
      });
    }
  }

  document.addEventListener("change", function (event) {
    const input = event.target;
    if (!input || !input.matches || !input.matches("[data-cloudinary-upload='1']")) return;
    const file = input.files && input.files[0];
    if (!file) return;
    uploadFile(input, file);
  });
})();
