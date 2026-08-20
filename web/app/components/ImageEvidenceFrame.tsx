"use client";

/* eslint-disable @next/next/no-img-element -- Case and upload images are no-store API/blob sources and must stay aligned with overlays. */

import type { CaseRecord } from "../lib/api";

type Detection = NonNullable<CaseRecord["detections"]>[number];

type ImageEvidenceFrameProps = {
  src: string;
  alt: string;
  width?: number;
  height?: number;
  detections?: Detection[];
  loading?: "eager" | "lazy";
  fetchPriority?: "high" | "low" | "auto";
  caption?: string;
  className?: string;
};

export default function ImageEvidenceFrame({
  src,
  alt,
  width,
  height,
  detections = [],
  loading = "lazy",
  fetchPriority = "auto",
  caption,
  className = "",
}: ImageEvidenceFrameProps) {
  return (
    <figure className={`v3-image-evidence ${className}`}>
      <div className="v3-image-canvas">
        <div className="v3-image-stage">
          <img src={src} alt={alt} width={width} height={height} loading={loading} fetchPriority={fetchPriority} decoding="async" />
          {detections.map((item, index) => {
            const [left, top, boxWidth, boxHeight] = item.bbox;
            return (
              <span
                className="v3-detection-box"
                key={`${item.class_id}-${index}`}
                style={{ left: `${left * 100}%`, top: `${top * 100}%`, width: `${boxWidth * 100}%`, height: `${boxHeight * 100}%` }}
              >
                <b>{item.class_name} {Math.round(item.confidence * 100)}%</b>
              </span>
            );
          })}
        </div>
      </div>
      {caption && <figcaption>{caption}</figcaption>}
    </figure>
  );
}
