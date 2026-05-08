export namespace main {
	
	export class Detection {
	    frame_name: string;
	    frame_index: number;
	    class_name: string;
	    confidence: number;
	    bbox: Record<string, number>;
	
	    static createFrom(source: any = {}) {
	        return new Detection(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.frame_name = source["frame_name"];
	        this.frame_index = source["frame_index"];
	        this.class_name = source["class_name"];
	        this.confidence = source["confidence"];
	        this.bbox = source["bbox"];
	    }
	}
	export class AnalyzeResult {
	    mode: string;
	    job_id: string;
	    detections_count: number;
	    detections: Detection[];
	    annotated_dir: string;
	    server_url: string;
	
	    static createFrom(source: any = {}) {
	        return new AnalyzeResult(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.mode = source["mode"];
	        this.job_id = source["job_id"];
	        this.detections_count = source["detections_count"];
	        this.detections = this.convertValues(source["detections"], Detection);
	        this.annotated_dir = source["annotated_dir"];
	        this.server_url = source["server_url"];
	    }
	
		convertValues(a: any, classs: any, asMap: boolean = false): any {
		    if (!a) {
		        return a;
		    }
		    if (a.slice && a.map) {
		        return (a as any[]).map(elem => this.convertValues(elem, classs));
		    } else if ("object" === typeof a) {
		        if (asMap) {
		            for (const key of Object.keys(a)) {
		                a[key] = new classs(a[key]);
		            }
		            return a;
		        }
		        return new classs(a);
		    }
		    return a;
		}
	}

}

