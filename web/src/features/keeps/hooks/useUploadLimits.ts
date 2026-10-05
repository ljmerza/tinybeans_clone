import { useQuery } from "@tanstack/react-query";

import { keepKeys } from "../api/queryKeys";
import { keepServices } from "../api/services";
import { DEFAULT_UPLOAD_LIMITS, type UploadLimits } from "../utils/mediaFiles";

/**
 * The server's upload limits, so an oversized file is turned away before it
 * is sent (a proxy in front may cap requests lower than the defaults). Falls
 * back to the defaults until the server answers or if it can't.
 */
export function useUploadLimits(): UploadLimits {
	const { data } = useQuery({
		queryKey: keepKeys.uploadLimits(),
		queryFn: () => keepServices.getUploadLimits(),
		select: (response) => response.data,
		staleTime: Number.POSITIVE_INFINITY,
	});
	return data ?? DEFAULT_UPLOAD_LIMITS;
}
